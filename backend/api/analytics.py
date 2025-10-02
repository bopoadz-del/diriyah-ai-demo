from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter

from backend.services.anomaly_detector import detect_anomalies
from backend.services.compliance_monitor import check_compliance

router = APIRouter()


_SAMPLE_STREAM: List[Dict[str, Any]] = [
    {
        "timestamp": "2024-04-01T09:00:00Z",
        "section": "Structure",
        "risk_score": 0.82,
        "risk_threshold": 0.6,
        "risk_drivers": ["supply chain", "weather"],
        "progress_percent": 45,
        "expected_progress_percent": 52,
        "schedule_delay_days": 4,
        "notes": "Concrete curing slower because of humidity.",
    },
    {
        "timestamp": "2024-04-03T15:00:00Z",
        "section": "Safety",
        "incidents": 2,
        "notes": "Two slip incidents recorded on scaffold, no lost time.",
    },
    {
        "timestamp": "2024-04-05T12:30:00Z",
        "section": "Commercial",
        "planned_cost": 1_200_000,
        "actual_cost": 1_320_000,
        "cost_tolerance_pct": 5,
        "notes": "Steel price surge impacted procurement package.",
    },
    {
        "timestamp": "2024-04-06T18:00:00Z",
        "section": "Schedule",
        "milestone": "Podium completion",
        "days_late": 5,
        "notes": "Awaiting façade bracket delivery for final pour.",
    },
]

_SAMPLE_COMPLIANCE_TEXT = (
    "Updated construction safety plan covers PPE requirements and emergency response. "
    "Weekly inspections recorded in the log. Hot work permits pending signature from fire marshal."
)

_SAMPLE_RULES = [
    {
        "id": "safety-plan",
        "description": "Safety plan must outline PPE and emergency response steps",
        "required_phrases": ["safety plan", "emergency response"],
        "severity": "high",
    },
    {
        "id": "inspection-cadence",
        "description": "Inspection cadence should mention weekly frequency",
        "required_phrases": ["weekly inspections"],
        "severity": "medium",
    },
    {
        "id": "permit-approval",
        "description": "Hot work permits must be approved prior to execution",
        "forbidden_phrases": ["pending signature"],
        "severity": "high",
        "recommendation": "Escalate with the fire marshal for immediate approval.",
    },
]


@router.get("/analytics/summary")
def analytics_summary() -> Dict[str, Any]:
    """Provide a deterministic analytics snapshot for local development."""

    anomalies = detect_anomalies(_SAMPLE_STREAM)
    compliance_findings = check_compliance(_SAMPLE_COMPLIANCE_TEXT, _SAMPLE_RULES)

    risk_alerts = [finding for finding in anomalies if finding["type"] == "risk"]
    schedule_alerts = [finding for finding in anomalies if finding["type"] == "schedule"]
    safety_alerts = [finding for finding in anomalies if finding["type"] == "safety"]
    cost_alerts = [finding for finding in anomalies if finding["type"] == "cost"]

    latest_progress = _latest_progress(_SAMPLE_STREAM)
    compliance_breaches = [finding for finding in compliance_findings if finding["status"] != "compliant"]

    overall_health = _determine_overall_health(risk_alerts, schedule_alerts, safety_alerts, compliance_breaches)

    return {
        "status": "ok",
        "generatedAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "data": {
            "overallHealth": overall_health,
            "riskAlerts": len(risk_alerts),
            "safetyIncidents": sum(alert["context"].get("incident_count", 1) for alert in safety_alerts),
            "scheduleVarianceDays": _aggregate_schedule_variance(schedule_alerts),
            "costVariancePct": round(sum(alert["context"].get("deviation_pct", 0.0) for alert in cost_alerts), 1),
            "latestProgress": latest_progress,
            "complianceBreaches": len(compliance_breaches),
            "nonCompliantRules": [finding["rule_id"] for finding in compliance_breaches],
        },
        "anomalies": anomalies,
        "compliance": compliance_findings,
    }


def _latest_progress(stream: List[Dict[str, Any]]) -> Dict[str, float]:
    latest_entry = None
    for entry in stream:
        if "progress_percent" not in entry:
            continue
        latest_entry = entry
    if not latest_entry:
        return {"actual": 0.0, "expected": 0.0}
    return {
        "actual": float(latest_entry.get("progress_percent", 0.0)),
        "expected": float(latest_entry.get("expected_progress_percent", 0.0)),
    }


def _aggregate_schedule_variance(schedule_alerts: List[Dict[str, Any]]) -> int:
    total = 0.0
    for alert in schedule_alerts:
        if "delay_days" in alert["context"]:
            total += float(alert["context"].get("delay_days", 0.0))
        elif "variance_percent" in alert["context"]:
            # Convert percentage variance into rough day equivalent assuming a
            # five-day working week; this keeps the stub realistic for dashboards.
            total += float(alert["context"].get("variance_percent", 0.0)) / 100 * 5
    return int(round(total))


def _determine_overall_health(
    risk_alerts: List[Dict[str, Any]],
    schedule_alerts: List[Dict[str, Any]],
    safety_alerts: List[Dict[str, Any]],
    compliance_breaches: List[Dict[str, Any]],
) -> str:
    if any(alert["severity"] == "critical" for alert in (*risk_alerts, *schedule_alerts, *safety_alerts)):
        return "at-risk"
    if compliance_breaches and any(breach["severity"] == "high" for breach in compliance_breaches):
        return "attention"
    if risk_alerts or schedule_alerts or safety_alerts:
        return "watch"
    return "on-track"
