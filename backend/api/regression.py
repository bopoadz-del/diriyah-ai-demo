"""Regression guard API endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.regression.guard import RegressionGuard
from backend.regression.models import PromotionRequest
from backend.regression.schemas import (
    PromotionApproveRequest,
    PromotionPromoteRequest,
    PromotionRequestCreate,
    PromotionRequestOut,
    RegressionCheckOut,
    ThresholdUpdateRequest,
)

router = APIRouter(prefix="/regression", tags=["Regression"])

guard = RegressionGuard()


@router.post("/requests", response_model=PromotionRequestOut)
def create_request(payload: PromotionRequestCreate, db: Session = Depends(get_db)) -> PromotionRequestOut:
    request = guard.create_request(
        db,
        component=payload.component,
        candidate_tag=payload.candidate_tag,
        workspace_id=payload.workspace_id,
        requested_by=payload.requested_by,
    )
    return PromotionRequestOut.model_validate(request)


@router.post("/requests/{request_id}/run-check", response_model=RegressionCheckOut)
def run_check(request_id: int, db: Session = Depends(get_db)) -> RegressionCheckOut:
    check = guard.run_check(db, request_id)
    return RegressionCheckOut.model_validate(check)


@router.post("/requests/{request_id}/approve", response_model=PromotionRequestOut)
def approve_request(
    request_id: int,
    payload: PromotionApproveRequest,
    db: Session = Depends(get_db),
) -> PromotionRequestOut:
    request = guard.approve(db, request_id, payload.approved_by)
    return PromotionRequestOut.model_validate(request)


@router.post("/requests/{request_id}/promote", response_model=PromotionRequestOut)
def promote_request(
    request_id: int,
    payload: PromotionPromoteRequest,
    db: Session = Depends(get_db),
) -> PromotionRequestOut:
    request = guard.promote(db, request_id, payload.actor_id)
    return PromotionRequestOut.model_validate(request)


@router.get("/requests", response_model=List[PromotionRequestOut])
def list_requests(
    component: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[PromotionRequestOut]:
    query = db.query(PromotionRequest)
    if component:
        query = query.filter(PromotionRequest.component == component)
    if status:
        query = query.filter(PromotionRequest.status == status)
    requests = query.order_by(PromotionRequest.created_at.desc()).limit(limit).all()
    return [PromotionRequestOut.model_validate(item) for item in requests]


@router.get("/requests/{request_id}", response_model=PromotionRequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)) -> PromotionRequestOut:
    request = db.query(PromotionRequest).filter(PromotionRequest.id == request_id).one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return PromotionRequestOut.model_validate(request)


@router.put("/thresholds/{component}")
def update_thresholds(
    component: str,
    payload: ThresholdUpdateRequest,
    db: Session = Depends(get_db),
) -> dict:
    threshold = guard.update_thresholds(
        db,
        component=component,
        updated_by=payload.updated_by,
        min_threshold=payload.min_threshold,
        max_drop=payload.max_drop,
        enabled=payload.enabled,
    )
    return {
        "component": threshold.component,
        "suite_name": threshold.suite_name,
        "min_threshold": threshold.min_threshold,
        "max_drop": threshold.max_drop,
        "enabled": threshold.enabled,
        "updated_at": threshold.updated_at.isoformat() if threshold.updated_at else None,
    }
