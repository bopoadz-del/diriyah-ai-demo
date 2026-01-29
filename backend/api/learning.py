"""API endpoints for learning feedback and dataset exports."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.backend.pdp.audit_logger import AuditLogger
from backend.backend.pdp.policy_engine import PolicyEngine
from backend.backend.pdp.schemas import PolicyRequest
from backend.events.emitter import emit_global
from backend.events.envelope import EventEnvelope
from backend.learning.datasets import export_dataset, get_dataset_builder
from backend.learning.models import (
    FeedbackEvent,
    FeedbackLabel,
    FeedbackReview,
    FeedbackReviewStatus,
    TrainingDataset,
)
from backend.learning.schemas import (
    ExportDatasetRequest,
    ExportDatasetResponse,
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackLabelRequest,
    FeedbackLabelResponse,
    FeedbackReviewRequest,
    FeedbackReviewResponse,
    LearningStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["Learning"])

def _safe_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _latest_review_statuses(db: Session, feedback_ids: list[int]) -> dict[int, FeedbackReviewStatus]:
    latest: dict[int, FeedbackReviewStatus] = {}
    if not feedback_ids:
        return latest
    reviews = (
        db.query(FeedbackReview)
        .filter(FeedbackReview.feedback_id.in_(feedback_ids))
        .order_by(FeedbackReview.feedback_id.asc(), FeedbackReview.created_at.desc())
        .all()
    )
    for review in reviews:
        if review.feedback_id not in latest:
            latest[review.feedback_id] = review.status
    return latest


@router.post("/feedback", response_model=FeedbackCreateResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(
    payload: FeedbackCreateRequest,
    db: Session = Depends(get_db),
) -> FeedbackCreateResponse:
    event = FeedbackEvent(
        workspace_id=payload.workspace_id,
        user_id=payload.user_id,
        source=payload.source,
        input_text=payload.input_text,
        output_text=payload.output_text,
        metadata_json=payload.metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info("Feedback captured", extra={"feedback_id": event.id, "workspace_id": payload.workspace_id})
    emit_global(
        EventEnvelope.build(
            event_type="learning.feedback.created",
            workspace_id=_safe_int(payload.workspace_id),
            actor_id=payload.user_id,
            source="learning",
            payload={
                "feedback_id": event.id,
                "workspace_id": payload.workspace_id,
                "user_id": payload.user_id,
                "source": payload.source,
            },
        )
    )
    return FeedbackCreateResponse(feedback_id=event.id)


@router.post("/feedback/{feedback_id}/label", response_model=FeedbackLabelResponse)
def add_feedback_label(
    feedback_id: int,
    payload: FeedbackLabelRequest,
    db: Session = Depends(get_db),
) -> FeedbackLabelResponse:
    feedback = db.query(FeedbackEvent).filter(FeedbackEvent.id == feedback_id).one_or_none()
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    label = FeedbackLabel(
        feedback_id=feedback_id,
        label_type=payload.label_type,
        label_json=payload.label_data,
    )
    db.add(label)
    db.commit()
    db.refresh(label)
    return FeedbackLabelResponse(label_id=label.id)


@router.post("/feedback/{feedback_id}/review", response_model=FeedbackReviewResponse)
def review_feedback(
    feedback_id: int,
    payload: FeedbackReviewRequest,
    db: Session = Depends(get_db),
) -> FeedbackReviewResponse:
    feedback = db.query(FeedbackEvent).filter(FeedbackEvent.id == feedback_id).one_or_none()
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    try:
        status_value = FeedbackReviewStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review status") from exc

    _evaluate_pdp(db, payload.reviewer_id or 0, "learning_review", feedback.workspace_id)

    review = FeedbackReview(
        feedback_id=feedback_id,
        reviewer_id=payload.reviewer_id,
        status=status_value,
        notes=payload.notes,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    emit_global(
        EventEnvelope.build(
            event_type="learning.feedback.reviewed",
            workspace_id=_safe_int(str(feedback.workspace_id)),
            actor_id=payload.reviewer_id,
            source="learning",
            payload={
                "feedback_id": feedback.id,
                "review_id": review.id,
                "status": status_value.value,
                "workspace_id": feedback.workspace_id,
            },
        )
    )
    return FeedbackReviewResponse(review_id=review.id)


@router.post(
    "/export-dataset/{dataset_name}",
    response_model=ExportDatasetResponse,
)
def export_dataset_api(
    dataset_name: str,
    payload: ExportDatasetRequest,
    db: Session = Depends(get_db),
) -> ExportDatasetResponse:
    try:
        get_dataset_builder(dataset_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    _evaluate_pdp(db, 0, "learning_export", payload.workspace_id)

    export_root = Path(os.getenv("LEARNING_EXPORT_DIR", "backend/learning/exports"))
    result = export_dataset(
        db,
        dataset_name=dataset_name,
        workspace_id=payload.workspace_id,
        export_dir=export_root,
        max_records=payload.max_records,
    )
    emit_global(
        EventEnvelope.build(
            event_type="learning.dataset.exported",
            workspace_id=_safe_int(payload.workspace_id),
            actor_id=None,
            source="learning",
            payload={
                "dataset_name": result.get("dataset_name"),
                "record_count": result.get("record_count"),
                "version_tag": result.get("version_tag"),
                "workspace_id": payload.workspace_id,
            },
        )
    )
    return ExportDatasetResponse(**result)


@router.get("/status", response_model=LearningStatusResponse)
def learning_status(
    workspace_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> LearningStatusResponse:
    feedback_query = db.query(FeedbackEvent)
    dataset_query = db.query(TrainingDataset)
    if workspace_id:
        feedback_query = feedback_query.filter(FeedbackEvent.workspace_id == workspace_id)
        dataset_query = dataset_query.filter(TrainingDataset.workspace_id == workspace_id)

    feedback_events = feedback_query.all()
    feedback_ids = [event.id for event in feedback_events]
    latest_reviews = _latest_review_statuses(db, feedback_ids)

    approved = sum(1 for status_value in latest_reviews.values() if status_value == FeedbackReviewStatus.APPROVED)
    pending = len(feedback_events) - len(latest_reviews)

    return LearningStatusResponse(
        workspace_id=workspace_id,
        feedback_total=len(feedback_events),
        feedback_approved=approved,
        feedback_pending_review=pending,
        datasets_exported=dataset_query.count(),
    )
