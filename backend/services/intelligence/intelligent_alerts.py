"""Intelligent alerting utilities built on uncertainty and causal analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import json
import logging
import os

import numpy as np
import pandas as pd

from .uncertainty_quantification import UncertaintyQuantifier, UncertaintyResult
from .causal_analysis import ConstructionCausalAnalyzer, CausalInsight

logger = logging.getLogger(__name__)


@dataclass
class IntelligentAlert:
    """Alert payload exposed to the API and WebSocket clients."""

    alert_id: str
    timestamp: datetime
    alert_type: str
    message: str
    severity: str
    confidence: float
    uncertainty_range: Tuple[float, float]
    root_cause_analysis: Dict[str, float]
    recommended_actions: List[Dict[str, Any]]
    expected_impact: Dict[str, float]
    escalation_required: bool
    auto_resolvable: bool
    context: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


class AlertIntelligenceSystem:
    """Generate enriched alerts using both uncertainty and causal analysis."""

    def __init__(self, uncertainty_quantifier: UncertaintyQuantifier, causal_analyzer: ConstructionCausalAnalyzer) -> None:
        self.uncertainty_quantifier = uncertainty_quantifier
        self.causal_analyzer = causal_analyzer
        self.alert_history: List[IntelligentAlert] = []
        self.websocket_connections: List[Any] = []

    async def process_event(self, event: Dict[str, Any]) -> Optional[IntelligentAlert]:
        probability = self._assess_alert_probability(event)
        if probability < 0.3:
            logger.debug("Event below alert threshold; probability=%.2f", probability)
            return None

        uncertainty = self._quantify_event_uncertainty(event)
        causal_insight: Optional[CausalInsight] = None
        if event.get("type") in {"delay", "cost_overrun", "quality_issue"}:
            causal_insight = self._analyze_root_cause(event)

        alert = self._create_intelligent_alert(event, uncertainty, causal_insight, probability)
        self.alert_history.append(alert)

        await self._broadcast_alert(alert)
        if alert.auto_resolvable:
            await self._trigger_auto_resolution(alert)
        return alert

    def _assess_alert_probability(self, event: Dict[str, Any]) -> float:
        probability = 0.0
        probability += 0.4 if event.get("delay_days", 0) > 5 else 0.0
        probability += 0.3 if event.get("cost_overrun_percentage", 0) > 10 else 0.0
        probability += 0.5 if event.get("safety_risk") else 0.0
        probability += 0.2 if event.get("quality_deviation", 0) > 0.1 else 0.0
        if event.get("project_phase") == "critical_path":
            probability *= 1.5
        return min(probability, 1.0)

    def _quantify_event_uncertainty(self, event: Dict[str, Any]) -> UncertaintyResult:
        features = self._event_to_features(event)
        try:
            results = self.uncertainty_quantifier.predict_with_uncertainty(features)
            return results[0]
        except Exception as exc:  # pragma: no cover - heuristic fallback
            logger.debug("Uncertainty estimation failed: %s", exc)
            return UncertaintyResult(
                prediction=0,
                confidence=0.6,
                uncertainty=0.4,
                confidence_interval=(0.5, 0.7),
                explanation="Heuristic uncertainty estimate",
                should_escalate=False,
            )

    def _analyze_root_cause(self, event: Dict[str, Any]) -> CausalInsight:
        project_data = self._get_project_context(event.get("project_id"))
        event_frame = pd.DataFrame([event])
        combined = pd.concat([project_data, event_frame], ignore_index=True, sort=False)
        target = self._determine_target_variable(event)
        return self.causal_analyzer.analyze_delay_causes(combined, target)

    def _create_intelligent_alert(self, event: Dict[str, Any], uncertainty: UncertaintyResult, causal: Optional[CausalInsight], probability: float) -> IntelligentAlert:
        severity = self._calculate_severity(event, uncertainty, probability)
        message = self._generate_alert_message(event, uncertainty, causal)
        escalation_required = severity in {"high", "critical"} or uncertainty.should_escalate or probability > 0.8
        auto_resolvable = severity == "low" and not escalation_required and causal is not None and bool(causal.recommended_interventions)
        root_causes = causal.root_causes if causal else {}
        actions = causal.recommended_interventions[:3] if causal else []
        impact = causal.expected_impact if causal else {}

        return IntelligentAlert(
            alert_id=self._generate_alert_id(),
            timestamp=datetime.utcnow(),
            alert_type=str(event.get("type", "unknown")),
            message=message,
            severity=severity,
            confidence=float(uncertainty.confidence),
            uncertainty_range=uncertainty.confidence_interval,
            root_cause_analysis=root_causes,
            recommended_actions=actions,
            expected_impact=impact,
            escalation_required=escalation_required,
            auto_resolvable=auto_resolvable,
            context=event,
        )

    def _generate_alert_message(self, event: Dict[str, Any], uncertainty: UncertaintyResult, causal: Optional[CausalInsight]) -> str:
        issue = event.get("description")
        if event.get("type") == "delay":
            issue = f"Schedule delay detected: {event.get('delay_days', 'N/A')} days"
        elif event.get("type") == "cost_overrun":
            issue = f"Cost overrun detected: {event.get('cost_overrun_percentage', 'N/A')}%"
        elif event.get("type") == "quality_issue":
            issue = issue or "Quality deviation detected"
        else:
            issue = issue or "Project issue detected"

        confidence_label = "high" if uncertainty.confidence > 0.8 else "moderate" if uncertainty.confidence > 0.6 else "low"
        parts = [f"{issue} [Confidence: {confidence_label} ({uncertainty.confidence:.0%})]"]

        if causal and causal.root_causes:
            top_cause = next(iter(causal.root_causes))
            parts.append(f"Primary cause: {top_cause}")
        if causal and causal.recommended_interventions:
            action = causal.recommended_interventions[0]
            parts.append(f"Recommended: {action['action']} (ROI {action['roi']:.0%})")
        return " | ".join(parts)

    def _calculate_severity(self, event: Dict[str, Any], uncertainty: UncertaintyResult, probability: float) -> str:
        delay = event.get("delay_days", 0)
        overrun = event.get("cost_overrun_percentage", 0)
        severity = "low"
        if delay > 30 or overrun > 25:
            severity = "critical"
        elif delay > 15 or overrun > 15:
            severity = "high"
        elif delay > 5 or overrun > 5:
            severity = "medium"

        if uncertainty.confidence < 0.5 and severity != "critical":
            order = ["low", "medium", "high", "critical"]
            severity_index = max(0, order.index(severity) - 1)
            severity = order[severity_index]
        return severity

    async def _broadcast_alert(self, alert: IntelligentAlert) -> None:
        if not self.websocket_connections:
            return
        payload = json.dumps(alert.to_dict())
        tasks = []
        for ws in list(self.websocket_connections):
            try:
                tasks.append(ws.send_text(payload))
            except Exception as exc:  # pragma: no cover - network errors
                logger.debug("Failed to queue WebSocket send: %s", exc)
                self.websocket_connections.remove(ws)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _trigger_auto_resolution(self, alert: IntelligentAlert) -> None:
        if not alert.recommended_actions:
            return
        action = alert.recommended_actions[0]
        logger.info("Auto-resolving alert %s with action %s", alert.alert_id, action.get("action"))
        await self._execute_intervention(action)

    async def _execute_intervention(self, action: Dict[str, Any]) -> None:
        logger.debug("Executing intervention: %s", action)
        await asyncio.sleep(0)

    def _event_to_features(self, event: Dict[str, Any]) -> np.ndarray:
        return np.array([
            event.get("delay_days", 0.0),
            event.get("cost_overrun_percentage", 0.0),
            event.get("resource_utilization", 0.0),
            event.get("weather_impact", 0.0),
            event.get("design_change_count", 0.0),
            event.get("quality_score", 1.0),
            event.get("safety_score", 1.0),
            1.0 if event.get("project_phase") == "critical_path" else 0.0,
        ], dtype=float)

    def _get_project_context(self, project_id: Optional[str]) -> pd.DataFrame:
        np.random.seed(abs(hash(project_id)) % (2**32))
        dates = pd.date_range(end=datetime.utcnow(), periods=60)
        return pd.DataFrame(
            {
                "date": dates,
                "daily_progress": np.random.uniform(0.4, 1.0, size=len(dates)),
                "resource_utilization": np.random.uniform(0.5, 1.0, size=len(dates)),
                "weather_impact": np.random.uniform(0.0, 0.3, size=len(dates)),
                "design_change_count": np.random.randint(0, 5, size=len(dates)),
                "planned_duration": np.random.uniform(0.8, 1.2, size=len(dates)),
                "actual_duration": np.random.uniform(0.9, 1.3, size=len(dates)),
                "planned_cost": np.random.uniform(0.8, 1.2, size=len(dates)),
                "actual_cost": np.random.uniform(0.9, 1.3, size=len(dates)),
            }
        )

    def _determine_target_variable(self, event: Dict[str, Any]) -> str:
        event_type = str(event.get("type", ""))
        if "delay" in event_type:
            return "schedule_delay"
        if "cost" in event_type:
            return "cost_overrun"
        if "quality" in event_type:
            return "quality_score"
        return "construction_progress"

    def _generate_alert_id(self) -> str:
        return f"ALERT-{os.urandom(4).hex().upper()}"
