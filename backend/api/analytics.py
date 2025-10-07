"""Analytics endpoints backed by Google Drive payloads with safe fallbacks."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Query

from backend.services.anomaly_detector import detect_anomalies
from backend.services.compliance_monitor import check_compliance
from backend.services.drive_payloads import load_json_resource, load_text_resource

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

_SAMPLE_ACTIVITY_LOG: List[Dict[str, Any]] = [
    {
        "id": "evt-001",
        "action": "message.sent",
        "user_id": "user-123",
        "message_id": "msg-001",
        "timestamp": "2024-04-10T09:15:00Z",
    },
    {
        "id": "evt-002",
        "action": "message.read",
        "user_id": "user-456",
        "message_id": "msg-002",
        "timestamp": "2024-04-10T09:45:00Z",
    },
    {
        "id": "evt-003",
        "action": "message.sent",
        "user_id": "user-123",
        "message_id": "msg-003",
        "timestamp": "2024-04-10T10:05:00Z",
    },
    {
        "id": "evt-004",
        "action": "message.flagged",
        "user_id": "user-789",
        "message_id": "msg-004",
        "timestamp": "2024-04-10T11:20:00Z",
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


def _drive_backed_stream(file_id: str | None) -> List[Dict[str, Any]]:
    payload = load_json_resource(file_id, env_var="ANALYTICS_DRIVE_FILE_ID", default={})
    stream = payload.get("stream") if isinstance(payload, dict) else None
    if isinstance(stream, list):
        return [dict(entry) for entry in stream]
    return [dict(entry) for entry in _SAMPLE_STREAM]


def _drive_backed_activity(file_id: str | None) -> List[Dict[str, Any]]:
    payload = load_json_resource(file_id, env_var="ANALYTICS_ACTIVITY_FILE_ID", default={})
    activity = payload.get("activity") if isinstance(payload, dict) else None
    if isinstance(activity, list):
        return [dict(entry) for entry in activity]
    return [dict(entry) for entry in _SAMPLE_ACTIVITY_LOG]


def _drive_backed_rules(file_id: str | None) -> List[Dict[str, Any]]:
    payload = load_json_resource(file_id, env_var="ANALYTICS_RULES_FILE_ID", default={})
    rules = payload.get("rules") if isinstance(payload, dict) else None
    if isinstance(rules, list):
        return [dict(rule) for rule in rules]
    return [dict(rule) for rule in _SAMPLE_RULES]


def _drive_backed_text(file_id: str | None) -> str:
    return load_text_resource(file_id, env_var="ANALYTICS_TEXT_FILE_ID", default=_SAMPLE_COMPLIANCE_TEXT)


@router.get("/analytics")
def analytics_log(
    activity_file_id: str | None = Query(
        default=None,
        description="Optional Drive file id containing analytics activity logs",
    ),
) -> List[Dict[str, Any]]:
    """Return activity logs sourced from Drive or fallback data."""

    return _drive_backed_activity(activity_file_id)


@router.get("/analytics/summary")
def analytics_summary(
    stream_file_id: str | None = Query(
        default=None,
        description="Optional Drive file id with analytics stream data",
    ),
    rules_file_id: str | None = Query(
        default=None,
        description="Optional Drive file id with compliance rules",
    ),
    text_file_id: str | None = Query(
        default=None,
        description="Optional Drive file id with compliance text",
    ),
) -> Dict[str, Any]:
    """Provide an analytics snapshot driven by Drive-backed payloads."""

    stream = _drive_backed_stream(stream_file_id)
    rules = _drive_backed_rules(rules_file_id)
    compliance_text = _drive_backed_text(text_file_id)

    anomalies = detect_anomalies(stream)
    compliance_findings = check_compliance(compliance_text, rules)

    risk_alerts = [finding for finding in anomalies if finding["type"] == "risk"]
    schedule_alerts = [finding for finding in anomalies if finding["type"] == "schedule"]
    safety_alerts = [finding for finding in anomalies if finding["type"] == "safety"]
    cost_alerts = [finding for finding in anomalies if finding["type"] == "cost"]

    latest_progress = _latest_progress(stream)
    compliance_breaches = [finding for finding in compliance_findings if finding["status"] != "compliant"]

    overall_health = _determine_overall_health(
        risk_alerts,
        schedule_alerts,
        safety_alerts,
        compliance_breaches,
    )

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


__all__ = ["router"]
