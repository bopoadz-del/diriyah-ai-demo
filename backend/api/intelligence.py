"""API surface for uncertainty quantification, causal analysis, and alerts."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional
import logging

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])
_alert_actions: Dict[str, str] = {}


@lru_cache(maxsize=1)
def _get_intelligence_stack():
    from backend.services.intelligence import (
        AlertIntelligenceSystem,
        ConstructionCausalAnalyzer,
        UncertaintyQuantifier,
        UncertaintyResult,
    )

    uncertainty_quantifier = UncertaintyQuantifier(model_type="classification")
    causal_analyzer = ConstructionCausalAnalyzer()
    alert_system = AlertIntelligenceSystem(uncertainty_quantifier, causal_analyzer)
    return uncertainty_quantifier, causal_analyzer, alert_system, UncertaintyResult


@router.post("/predict-with-uncertainty")
async def predict_with_uncertainty(request: Dict[str, Any]) -> Dict[str, Any]:
    uncertainty_quantifier, _, _, _ = _get_intelligence_stack()
    features = request.get("features")
    if features is None:
        raise HTTPException(status_code=400, detail="Missing 'features' in request body")

    features_array = np.asarray(features, dtype=float)
    if features_array.ndim == 1:
        features_array = features_array.reshape(1, -1)
    if features_array.size == 0:
        raise HTTPException(status_code=400, detail="At least one feature vector is required")

    try:
        results = uncertainty_quantifier.predict_with_uncertainty(features_array)
    except Exception as exc:  # pragma: no cover - defensive guard for misconfigured models
        logger.exception("Uncertainty prediction failed")
        raise HTTPException(status_code=500, detail=f"Failed to compute uncertainty: {exc}") from exc
    payload = [
        {
            "prediction": result.prediction,
            "confidence": result.confidence,
            "uncertainty": result.uncertainty,
            "confidence_interval": result.confidence_interval,
            "explanation": result.explanation,
            "should_escalate": result.should_escalate,
        }
        for result in results
    ]
    return {"predictions": payload}


@router.post("/analyze-delay-causes")
async def analyze_delay_causes(request: Dict[str, Any]) -> Dict[str, Any]:
    _, causal_analyzer, _, _ = _get_intelligence_stack()
    project_data = request.get("project_data")
    if project_data is None:
        raise HTTPException(status_code=400, detail="Missing 'project_data' in request body")
    target = request.get("target_variable", "schedule_delay")

    data_frame = pd.DataFrame(project_data)
    insight = causal_analyzer.analyze_delay_causes(data_frame, target)
    return {
        "root_causes": insight.root_causes,
        "causal_effect": insight.causal_effect,
        "confidence_interval": insight.confidence_interval,
        "recommended_interventions": insight.recommended_interventions,
        "expected_impact": insight.expected_impact,
        "robustness_check": insight.robustness_check,
    }


@router.post("/process-intelligent-alert")
async def process_intelligent_alert(event: Dict[str, Any]) -> Dict[str, Any]:
    _, _, alert_system, _ = _get_intelligence_stack()
    alert = await alert_system.process_event(event)
    if alert is None:
        return {"alert_generated": False, "reason": "Event below alert threshold"}
    return {"alert_generated": True, "alert": alert.to_dict()}


@router.post("/simulate-intervention")
async def simulate_intervention(payload: Dict[str, Any]) -> Dict[str, Any]:
    intervention = payload.get("intervention")
    if intervention is None:
        raise HTTPException(status_code=400, detail="Missing 'intervention' in request body")
    effect = float(intervention.get("effect_size", 0.0))
    target_change = float(intervention.get("target_change", 0.0))
    confidence = min(0.95, max(0.4, 0.7 + abs(effect)))
    schedule_improvement = abs(effect * target_change) * 30.0
    cost_savings = max(0.0, schedule_improvement * 10000.0 - float(intervention.get("cost", 0.0)))
    return {
        "schedule_improvement": round(schedule_improvement, 2),
        "cost_savings": round(cost_savings, 2),
        "confidence": round(confidence, 2),
    }


@router.post("/alert-action")
async def alert_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    alert_id = payload.get("alertId")
    action = payload.get("action")
    if not alert_id or not action:
        raise HTTPException(status_code=400, detail="'alertId' and 'action' are required")
    _alert_actions[alert_id] = action
    return {"status": "ok"}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> Dict[str, Any]:
    _alert_actions[alert_id] = "acknowledged"
    return {"status": "acknowledged"}


@router.post("/enhanced-chat")
async def enhanced_chat(request: Dict[str, Any]) -> Dict[str, Any]:
    query = str(request.get("query", "")).strip()
    context = request.get("context", {})
    response_text = build_chat_response(query)

    features = extract_features_from_query(query)
    try:
        uncertainty_quantifier, _, _, _ = _get_intelligence_stack()
        uncertainty_result = uncertainty_quantifier.predict_with_uncertainty(features)[0]
    except Exception as exc:  # pragma: no cover - fallback for unexpected runtime issues
        logger.exception("Enhanced chat uncertainty estimation failed")

        class _FallbackResult:
            prediction = None
            confidence = 0.6
            uncertainty = 0.4
            confidence_interval = (0.5, 0.7)
            explanation = "Uncertainty service temporarily unavailable"
            should_escalate = False

        uncertainty_result = _FallbackResult()

    causal_block: Optional[Dict[str, Any]] = None
    if any(keyword in query.lower() for keyword in ["delay", "late", "overrun", "issue"]):
        project_data = get_project_data_from_context(context)
        if not project_data.empty:
            _, causal_analyzer, _, _ = _get_intelligence_stack()
            insight = causal_analyzer.analyze_delay_causes(project_data)
            causal_block = {
                "identified": bool(insight.root_causes),
                "top_causes": list(insight.root_causes.items())[:3],
                "recommended_action": insight.recommended_interventions[0] if insight.recommended_interventions else None,
                "expected_impact": insight.expected_impact,
            }
    return {
        "response": response_text,
        "confidence": uncertainty_result.confidence,
        "uncertainty_bounds": uncertainty_result.confidence_interval,
        "confidence_explanation": uncertainty_result.explanation,
        "causal_analysis": causal_block,
        "actionable_insight": build_actionable_insight(causal_block),
    }


@router.websocket("/alerts")
async def websocket_alerts(websocket: WebSocket) -> None:
    _, _, alert_system, _ = _get_intelligence_stack()
    await websocket.accept()
    alert_system.websocket_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        alert_system.websocket_connections.remove(websocket)


def extract_features_from_query(query: str) -> np.ndarray:
    length = len(query)
    delay_keywords = sum(word in query.lower() for word in ["delay", "late", "slip"])
    cost_keywords = sum(word in query.lower() for word in ["cost", "budget", "overrun"])
    return np.array([[length / 100.0, delay_keywords, cost_keywords, 1.0]])


def get_project_data_from_context(context: Dict[str, Any]) -> pd.DataFrame:
    project_data = context.get("project_data")
    if isinstance(project_data, list):
        return pd.DataFrame(project_data)
    return pd.DataFrame()


def build_chat_response(query: str) -> str:
    if not query:
        return "How can I support your project today?"
    return f"Here is the latest analysis regarding: {query}"


def build_actionable_insight(causal_block: Optional[Dict[str, Any]]) -> Optional[str]:
    if not causal_block or not causal_block.get("recommended_action"):
        return None
    action = causal_block["recommended_action"]
    roi = action.get("roi")
    roi_text = f" with an ROI of {roi:.0%}" if isinstance(roi, (int, float)) else ""
    return f"Recommended action: {action.get('action')}{roi_text}."
