"""Regression guard logic for promotion gating."""

from __future__ import annotations

import importlib
import importlib.util
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.ops.regression_guard import RegressionGuard as OpsRegressionGuard
from backend.regression.models import (
    CurrentComponentVersion,
    PromotionRequest,
    RegressionCheck,
    RegressionThreshold,
)
from backend.regression.pdp_gate import require_admin, write_audit

_COMPONENTS = {
    "intent_router",
    "tool_router",
    "ule_linking",
    "pdp_policies",
    "prompt_templates",
}

_SUITE_MAPPING = {
    "ule_linking": "linking",
    "pdp_policies": "pdp",
    "intent_router": "runtime",
    "tool_router": "runtime",
    "prompt_templates": "runtime",
}


def _safe_int(value: Optional[str]) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class RegressionGuard:
    def create_request(
        self,
        db: Session,
        component: str,
        candidate_tag: str,
        workspace_id: Optional[str] = None,
        requested_by: Optional[int] = None,
    ) -> PromotionRequest:
        if component not in _COMPONENTS:
            raise HTTPException(status_code=400, detail="Unknown component")

        baseline_tag = self._get_or_seed_baseline(db, component)
        self._ensure_thresholds(db, component)

        request = PromotionRequest(
            workspace_id=workspace_id,
            component=component,
            baseline_tag=baseline_tag,
            candidate_tag=candidate_tag,
            status="requested",
            requested_by=requested_by,
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    def run_check(self, db: Session, request_id: int) -> RegressionCheck:
        request = db.query(PromotionRequest).filter(PromotionRequest.id == request_id).one_or_none()
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        suite_name = _SUITE_MAPPING.get(request.component)
        if not suite_name:
            raise HTTPException(status_code=400, detail="Suite mapping missing")

        thresholds = self._ensure_thresholds(db, request.component)
        if not thresholds.enabled:
            raise HTTPException(status_code=400, detail="Regression checks disabled for component")

        request.status = "running"
        db.commit()

        baseline_run_id, baseline_score, eval_threshold, baseline_report = self._run_eval_suite(
            suite_name,
            request.baseline_tag,
            request.workspace_id,
        )
        candidate_run_id, candidate_score, candidate_threshold, candidate_report = self._run_eval_suite(
            suite_name,
            request.candidate_tag,
            request.workspace_id,
        )

        min_threshold = eval_threshold or candidate_threshold or thresholds.min_threshold
        report: Dict[str, object] = {
            "baseline": baseline_report,
            "candidate": candidate_report,
        }

        passed = False
        drop_value = None
        if min_threshold is None:
            report["error"] = "Minimum threshold is not configured"
        elif baseline_score is None or candidate_score is None:
            report["error"] = "Tagged evaluation not supported"
        else:
            drop_value = baseline_score - candidate_score
            passed = candidate_score >= min_threshold and drop_value <= thresholds.max_drop

        request.status = "pass" if passed else "fail"
        request.updated_at = datetime.now(timezone.utc)

        check = RegressionCheck(
            promotion_request_id=request.id,
            suite_name=suite_name,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            min_threshold=min_threshold or 0.0,
            max_drop=thresholds.max_drop,
            drop_value=drop_value,
            passed=passed,
            report_json=report,
        )
        db.add(check)
        db.commit()
        db.refresh(check)
        return check

    def approve(self, db: Session, request_id: int, approved_by: int) -> PromotionRequest:
        request = db.query(PromotionRequest).filter(PromotionRequest.id == request_id).one_or_none()
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.status != "pass":
            raise HTTPException(status_code=400, detail="Request must pass regression checks before approval")

        context = self._build_context(request)
        require_admin(
            db,
            approved_by,
            "regression.approve",
            f"regression:promotion_request:{request.id}",
            context,
        )

        request.status = "approved"
        request.approved_by = approved_by
        db.commit()
        db.refresh(request)
        EventEmitter(db=db).emit(
            EventEnvelope.create(
                event_type="regression.approved",
                source="regression",
                workspace_id=_safe_int(request.workspace_id),
                actor_id=approved_by,
                correlation_id=None,
                payload={
                    "component": request.component,
                    "candidate_tag": request.candidate_tag,
                    "baseline_tag": request.baseline_tag,
                    "request_id": request.id,
                },
            )
        )
        write_audit(
            db,
            approved_by,
            "regression.approve",
            f"regression:promotion_request:{request.id}",
            {**context, "decision": "allow", "message": "approved"},
        )
        return request

    def promote(self, db: Session, request_id: int, actor_id: int) -> PromotionRequest:
        request = db.query(PromotionRequest).filter(PromotionRequest.id == request_id).one_or_none()
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.status != "approved":
            raise HTTPException(status_code=400, detail="Request must be approved before promotion")
        latest_check = (
            db.query(RegressionCheck)
            .filter(RegressionCheck.promotion_request_id == request.id)
            .order_by(RegressionCheck.created_at.desc())
            .first()
        )
        if not latest_check or not latest_check.passed:
            raise HTTPException(status_code=400, detail="Regression checks must pass before promotion")

        context = self._build_context(request)
        require_admin(
            db,
            actor_id,
            "regression.promote",
            f"regression:promotion_request:{request.id}",
            context,
        )

        ops_guard = OpsRegressionGuard()
        workspace_id = _safe_int(request.workspace_id)
        allowed, reason = ops_guard.should_promote(request.component, workspace_id, db)
        if not allowed:
            raise HTTPException(status_code=409, detail=reason)

        current = db.query(CurrentComponentVersion).filter(CurrentComponentVersion.component == request.component).one_or_none()
        if current:
            current.current_tag = request.candidate_tag
        else:
            current = CurrentComponentVersion(component=request.component, current_tag=request.candidate_tag)
            db.add(current)

        request.status = "promoted"
        db.commit()
        db.refresh(request)
        EventEmitter(db=db).emit(
            EventEnvelope.create(
                event_type="regression.promoted",
                source="regression",
                workspace_id=workspace_id,
                actor_id=actor_id,
                correlation_id=None,
                payload={
                    "component": request.component,
                    "candidate_tag": request.candidate_tag,
                    "baseline_tag": request.baseline_tag,
                    "request_id": request.id,
                },
            )
        )
        write_audit(
            db,
            actor_id,
            "regression.promote",
            f"regression:promotion_request:{request.id}",
            {**context, "decision": "allow", "message": "promoted"},
        )
        return request

    def update_thresholds(
        self,
        db: Session,
        component: str,
        updated_by: int,
        min_threshold: Optional[float] = None,
        max_drop: Optional[float] = None,
        enabled: Optional[bool] = None,
    ) -> RegressionThreshold:
        if component not in _COMPONENTS:
            raise HTTPException(status_code=400, detail="Unknown component")

        threshold = self._ensure_thresholds(db, component)
        context = {
            "component": component,
            "suite_name": threshold.suite_name,
        }
        require_admin(
            db,
            updated_by,
            "regression.thresholds.update",
            f"regression:thresholds:{component}",
            context,
        )

        if min_threshold is not None:
            threshold.min_threshold = min_threshold
        if max_drop is not None:
            threshold.max_drop = max_drop
        if enabled is not None:
            threshold.enabled = enabled
        db.commit()
        db.refresh(threshold)
        write_audit(
            db,
            updated_by,
            "regression.thresholds.update",
            f"regression:thresholds:{component}",
            {**context, "decision": "allow", "message": "thresholds updated"},
        )
        return threshold

    def _get_or_seed_baseline(self, db: Session, component: str) -> str:
        current = db.query(CurrentComponentVersion).filter(CurrentComponentVersion.component == component).one_or_none()
        if current:
            return current.current_tag
        current = CurrentComponentVersion(component=component, current_tag="baseline:v1")
        db.add(current)
        db.commit()
        db.refresh(current)
        return current.current_tag

    def _ensure_thresholds(self, db: Session, component: str) -> RegressionThreshold:
        threshold = db.query(RegressionThreshold).filter(RegressionThreshold.component == component).one_or_none()
        if threshold:
            return threshold
        suite_name = _SUITE_MAPPING.get(component)
        if not suite_name:
            raise HTTPException(status_code=400, detail="Suite mapping missing")
        threshold = RegressionThreshold(component=component, suite_name=suite_name, max_drop=0.02, enabled=True)
        db.add(threshold)
        db.commit()
        db.refresh(threshold)
        return threshold

    def _run_eval_suite(
        self,
        suite_name: str,
        tag: str,
        workspace_id: Optional[str],
    ) -> Tuple[Optional[int], Optional[float], Optional[float], Dict[str, object]]:
        runner = self._load_eval_runner()
        if runner is None:
            return None, None, None, {"error": "tagged evaluation not supported"}

        result = runner(suite_name=suite_name, tag=tag, workspace_id=workspace_id)
        if isinstance(result, dict):
            return (
                result.get("run_id"),
                result.get("score"),
                result.get("min_threshold"),
                result,
            )
        if isinstance(result, (list, tuple)) and len(result) >= 2:
            run_id = result[0]
            score = result[1]
            min_threshold = result[2] if len(result) > 2 else None
            return run_id, score, min_threshold, {"result": result}
        return None, None, None, {"error": "tagged evaluation not supported"}

    def _load_eval_runner(self):
        spec = importlib.util.find_spec("backend.services.evaluation_harness")
        if spec is None:
            return None
        module = importlib.import_module("backend.services.evaluation_harness")
        return getattr(module, "run_regression_suite", None)

    @staticmethod
    def _build_context(request: PromotionRequest) -> dict:
        return {
            "workspace_id": request.workspace_id,
            "component": request.component,
            "baseline_tag": request.baseline_tag,
            "candidate_tag": request.candidate_tag,
        }
