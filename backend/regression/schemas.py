"""Pydantic schemas for regression guard APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PromotionRequestCreate(BaseModel):
    component: str
    candidate_tag: str
    workspace_id: Optional[str] = None
    requested_by: Optional[int] = None


class PromotionRequestOut(BaseModel):
    id: int
    component: str
    baseline_tag: str
    candidate_tag: str
    status: str
    workspace_id: Optional[str]
    requested_by: Optional[int]
    approved_by: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegressionCheckOut(BaseModel):
    id: int
    promotion_request_id: int
    suite_name: str
    baseline_score: Optional[float]
    candidate_score: Optional[float]
    min_threshold: float
    max_drop: float
    drop_value: Optional[float]
    passed: bool

    model_config = ConfigDict(from_attributes=True)


class PromotionApproveRequest(BaseModel):
    approved_by: int


class PromotionPromoteRequest(BaseModel):
    actor_id: int


class ThresholdUpdateRequest(BaseModel):
    updated_by: int
    min_threshold: Optional[float] = None
    max_drop: Optional[float] = None
    enabled: Optional[bool] = None
