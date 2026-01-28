"""Pydantic schemas for learning feedback API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace identifier")
    user_id: Optional[int] = Field(default=None, description="Optional user id")
    source: Optional[str] = Field(default=None, description="Source of feedback")
    input_text: str = Field(..., description="Prompt or input text")
    output_text: Optional[str] = Field(default=None, description="System output")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Extra metadata")


class FeedbackCreateResponse(BaseModel):
    feedback_id: int


class FeedbackLabelRequest(BaseModel):
    label_type: str = Field(..., description="Label type name")
    label_data: Dict[str, Any] = Field(..., description="Label payload")


class FeedbackLabelResponse(BaseModel):
    label_id: int


class FeedbackReviewRequest(BaseModel):
    reviewer_id: Optional[int] = Field(default=None, description="Reviewer user id")
    status: str = Field(..., description="approved, rejected, needs_changes")
    notes: Optional[str] = Field(default=None, description="Review notes")


class FeedbackReviewResponse(BaseModel):
    review_id: int


class ExportDatasetRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace identifier")
    max_records: Optional[int] = Field(default=None, description="Limit number of records")


class ExportDatasetResponse(BaseModel):
    dataset_name: str
    version_tag: str
    record_count: int
    dataset_path: str
    manifest_path: str
    manifest: Dict[str, Any]


class LearningStatusResponse(BaseModel):
    workspace_id: Optional[str]
    feedback_total: int
    feedback_approved: int
    feedback_pending_review: int
    datasets_exported: int
