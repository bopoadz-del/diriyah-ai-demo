"""API endpoints for learning feedback and dataset exports."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from backend.backend.db import get_db
from backend.backend.pdp.audit_logger import AuditLogger
from backend.backend.pdp.policy_engine import PolicyEngine
from backend.backend.pdp.schemas import PolicyRequest
from backend.learning.builders import DATASET_BUILDERS
from backend.learning.models import FeedbackEvent
from backend.learning.service import (
    add_label,
    create_feedback,
    export_dataset,
    is_feedback_approved,
    review_feedback,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["Learning"])


class FeedbackCreateRequest(BaseModel):
    workspace_id: str
    event_type: str
    event_payload: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[int] = None


class FeedbackLabelRequest(BaseModel):
    label_type: str
    label_value: str
    labeled_by: Optional[int] = None


class FeedbackReviewRequest(BaseModel):
    decision: str = Field(..., description="approved or rejected")
    reviewer_id: Optional[int] = None
    notes: Optional[str] = None


class ExportDatasetRequest(BaseModel):
    workspace_id: str
    description: Optional[str] = None
    created_by: Optional[int] = None


def _parse_user_id(x_user_id: Optional[str], fallback: Optional[int] = None) -> int:
    if x_user_id:
        try:
            return int(x_user_id)
        except ValueError:
            return fallback or 0
    return fallback or 0


def _evaluate_pdp(db: Session, user_id: int, action: str, workspace_id: str) -> None:
    engine = PolicyEngine(db)
    request = PolicyRequest(
        user_id=user_id,
        action=action,
        resource_type="workspace",
        resource_id=None,
        context={"project_id": workspace_id, "workspace_id": workspace_id},
    )
    decision = engine.evaluate(request)
    AuditLogger(db).log_decision(
        user_id=user_id,
        action=action,
        resource_type="workspace",
        resource_id=None,
        decision="allow" if decision.allowed else "deny",
        metadata={"reason": decision.reason, "workspace_id": workspace_id},
    )
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def capture_feedback(
    payload: FeedbackCreateRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    user_id = _parse_user_id(x_user_id, payload.user_id)
    feedback = create_feedback(
        db,
        workspace_id=payload.workspace_id,
        event_type=payload.event_type,
        event_payload=payload.event_payload,
        user_id=user_id or None,
    )
    return {"feedback_id": feedback.id}


@router.post("/feedback/{feedback_id}/label", status_code=status.HTTP_201_CREATED)
def label_feedback(
    feedback_id: int,
    payload: FeedbackLabelRequest,
    db: Session = Depends(get_db),
):
    feedback = db.query(FeedbackEvent).filter(FeedbackEvent.id == feedback_id).one_or_none()
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    label = add_label(
        db,
        feedback_id=feedback_id,
        label_type=payload.label_type,
        label_value=payload.label_value,
        labeled_by=payload.labeled_by,
    )
    return {"label_id": label.id}


@router.post("/feedback/{feedback_id}/review", status_code=status.HTTP_201_CREATED)
def review_feedback_endpoint(
    feedback_id: int,
    payload: FeedbackReviewRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    feedback = db.query(FeedbackEvent).filter(FeedbackEvent.id == feedback_id).one_or_none()
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    reviewer_id = _parse_user_id(x_user_id, payload.reviewer_id)
    _evaluate_pdp(db, reviewer_id, "learning_review", feedback.workspace_id)
    review = review_feedback(
        db,
        feedback_id=feedback_id,
        decision=payload.decision,
        reviewer_id=reviewer_id or None,
        notes=payload.notes,
    )
    return {"review_id": review.id}


@router.post("/export-dataset/{dataset_name}")
def export_dataset_endpoint(
    dataset_name: str,
    payload: ExportDatasetRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    if dataset_name not in DATASET_BUILDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown dataset")
    user_id = _parse_user_id(x_user_id, payload.created_by)
    _evaluate_pdp(db, user_id, "learning_export", payload.workspace_id)
    result = export_dataset(
        db,
        dataset_name=dataset_name,
        workspace_id=payload.workspace_id,
        created_by=user_id or None,
        description=payload.description,
    )
    return JSONResponse(
        content={
            "dataset_id": result.dataset.id,
            "manifest": result.manifest,
        }
    )


@router.get("/status")
def learning_status(
    workspace_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    feedback_query = db.query(FeedbackEvent)
    if workspace_id:
        feedback_query = feedback_query.filter(FeedbackEvent.workspace_id == workspace_id)

    feedback_items = feedback_query.options(joinedload(FeedbackEvent.reviews)).all()
    feedback_total = len(feedback_items)
    approved_count = 0
    for feedback in feedback_items:
        if is_feedback_approved(feedback.reviews):
            approved_count += 1
    return {
        "workspace_id": workspace_id,
        "feedback_total": feedback_total,
        "approved_feedback_total": approved_count,
    }
