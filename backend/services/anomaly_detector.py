"""Rule based anomaly detection for construction telemetry.

The helper inspects heterogenous dictionaries coming from planning,
operations and safety systems.  It looks for well known signals that
should trigger follow-up by the analytics dashboard and returns a list
of structured findings.  The implementation purposely favours clear
heuristics over statistical models so the behaviour is predictable in
tests and for debugging inside Render deployments.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


Severity = str


def detect_anomalies(data_stream: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Inspect a project telemetry stream and report notable deviations.

    Parameters
    ----------
    data_stream:
        A list of dictionaries produced by schedulers, ERP exports or on-site
        logs.  The function is resilient to missing keys and silently skips
        malformed entries.

    Returns
    -------
    list
        Structured anomaly records with the following keys:

        ``type``
            Category of the anomaly (``risk``, ``schedule``, ``cost``,
            ``safety`` or ``quality``).
        ``severity``
            One of ``low``, ``medium``, ``high`` or ``critical`` depending on
            the magnitude of the finding.
        ``message``
            Human readable description suitable for dashboards.
        ``timestamp``
            Original timestamp if available.
        ``context``
            Machine readable fields that triggered the anomaly.
    """

    findings: List[Dict[str, Any]] = []

    for entry in data_stream or []:
        if not isinstance(entry, dict):
            continue

        timestamp = entry.get("timestamp")

        def add_finding(anomaly_type: str, severity: Severity, message: str, *, context: Optional[Dict[str, Any]] = None) -> None:
            findings.append(
                {
                    "type": anomaly_type,
                    "severity": severity,
                    "message": message,
                    "timestamp": timestamp,
                    "context": context or {},
                }
            )

        _check_risk(entry, add_finding)
        _check_schedule(entry, add_finding)
        _check_cost(entry, add_finding)
        _check_safety(entry, add_finding)
        _check_quality(entry, add_finding)

    # Sort by severity to keep the most pressing anomalies at the top of the
    # dashboard.  The ordering is stable for tests which makes assertions
    # deterministic.
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda finding: severity_order.get(finding["severity"], 99))
    return findings


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _check_risk(entry: Dict[str, Any], add_finding) -> None:
    risk_score = _to_float(entry.get("risk_score"))
    if risk_score is None:
        return

    risk_threshold = _to_float(entry.get("risk_threshold")) or 0.7
    if risk_score <= risk_threshold:
        return

    severity: Severity
    if risk_score >= 0.9:
        severity = "critical"
    elif risk_score >= (risk_threshold + 0.15):
        severity = "high"
    else:
        severity = "medium"

    add_finding(
        "risk",
        severity,
        f"Risk score {risk_score:.2f} exceeds threshold {risk_threshold:.2f} for {entry.get('section', 'project segment')}",
        context={
            "risk_score": risk_score,
            "risk_threshold": risk_threshold,
            "drivers": entry.get("risk_drivers", []),
        },
    )


def _check_schedule(entry: Dict[str, Any], add_finding) -> None:
    progress = _to_float(entry.get("progress_percent"))
    expected = _to_float(entry.get("expected_progress_percent"))
    tolerance = _to_float(entry.get("variance_tolerance"))
    tolerance = tolerance if tolerance is not None else 5.0

    if progress is not None and expected is not None:
        variance = expected - progress
        if variance > tolerance:
            severity: Severity = "high" if variance >= tolerance * 2 else "medium"
            add_finding(
                "schedule",
                severity,
                f"Progress trailing plan by {variance:.1f} percentage points",
                context={
                    "expected_progress_percent": expected,
                    "actual_progress_percent": progress,
                    "variance_percent": variance,
                },
            )

    delay_days = _to_float(entry.get("schedule_delay_days")) or _to_float(entry.get("days_late"))
    if delay_days and delay_days > 0:
        severity = "critical" if delay_days >= 14 else ("high" if delay_days >= 7 else "medium")
        add_finding(
            "schedule",
            severity,
            f"Milestone late by {int(delay_days)} days",
            context={
                "milestone": entry.get("milestone"),
                "delay_days": delay_days,
            },
        )


def _check_cost(entry: Dict[str, Any], add_finding) -> None:
    planned_cost = _to_float(entry.get("planned_cost"))
    actual_cost = _to_float(entry.get("actual_cost"))
    if planned_cost is None or actual_cost is None or planned_cost == 0:
        return

    deviation_pct = ((actual_cost - planned_cost) / planned_cost) * 100
    tolerance_pct = _to_float(entry.get("cost_tolerance_pct")) or 5.0

    if deviation_pct <= tolerance_pct:
        return

    severity: Severity = "high" if deviation_pct >= tolerance_pct * 2 else "medium"

    add_finding(
        "cost",
        severity,
        f"Cost overrun of {deviation_pct:.1f}% detected",
        context={
            "planned_cost": planned_cost,
            "actual_cost": actual_cost,
            "deviation_pct": deviation_pct,
        },
    )


def _check_safety(entry: Dict[str, Any], add_finding) -> None:
    incidents = entry.get("incidents") or entry.get("safety_incidents") or entry.get("incident_count")
    if incidents:
        try:
            incident_count = int(incidents)
        except (TypeError, ValueError):
            incident_count = 0

        if incident_count > 0:
            severity: Severity
            if incident_count >= 3 or _contains_any(entry.get("notes", ""), ["lost time", "hospitalisation", "hospitalization", "major"]):
                severity = "critical"
            elif incident_count == 2:
                severity = "high"
            else:
                severity = "medium"

            add_finding(
                "safety",
                severity,
                f"Recorded {incident_count} safety incident(s)",
                context={
                    "incident_count": incident_count,
                    "notes": entry.get("notes"),
                },
            )

    if _contains_any(entry.get("notes", ""), ["near miss", "near-miss", "ppe non-compliance"]):
        add_finding(
            "safety",
            "low",
            "Near miss reported – schedule refresher training",
            context={"notes": entry.get("notes")},
        )


def _check_quality(entry: Dict[str, Any], add_finding) -> None:
    defects = entry.get("defects") or entry.get("punch_items")
    if defects:
        try:
            defect_count = int(defects)
        except (TypeError, ValueError):
            defect_count = 0

        if defect_count > 0:
            severity: Severity = "high" if defect_count >= 5 else "medium"
            add_finding(
                "quality",
                severity,
                f"{defect_count} quality punch list item(s) logged",
                context={"defects": defect_count, "location": entry.get("section")},
            )

    if _contains_any(entry.get("notes", ""), ["rework", "non-conformance", "failed inspection"]):
        add_finding(
            "quality",
            "medium",
            "Quality non-conformance requires follow-up",
            context={"notes": entry.get("notes"), "inspection": entry.get("inspection")},
        )
