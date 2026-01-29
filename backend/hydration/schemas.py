"""Pydantic schemas for hydration API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.hydration.models import (
    AlertCategory,
    AlertSeverity,
    DocumentType,
    HydrationRunStatus,
    HydrationStatus,
    HydrationTrigger,
    RunItemAction,
    RunItemStatus,
    SourceType,
)


class WorkspaceSourceBase(BaseModel):
    workspace_id: str
    source_type: SourceType
    name: str
    config_json: Dict[str, Any] = Field(default_factory=dict)
    secrets_ref: Optional[str] = None
    is_enabled: bool = True


class WorkspaceSourceCreate(WorkspaceSourceBase):
    pass


class WorkspaceSourceUpdate(BaseModel):
    name: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    secrets_ref: Optional[str] = None
    is_enabled: Optional[bool] = None


class WorkspaceSourceOut(WorkspaceSourceBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HydrationStatusOut(BaseModel):
    workspace_id: str
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    status: HydrationStatus
    last_error: Optional[str]
    alerts: List["HydrationAlertOut"] = Field(default_factory=list)
    recent_runs: List["HydrationRunOut"] = Field(default_factory=list)


class HydrationRunOut(BaseModel):
    id: int
    workspace_id: str
    started_at: datetime
    finished_at: Optional[datetime]
    trigger: HydrationTrigger
    status: HydrationRunStatus
    sources_count: int
    files_seen: int
    files_new: int
    files_updated: int
    files_downloaded: int
    files_extracted: int
    files_indexed: int
    files_ule_processed: int
    files_failed: int
    error_summary: Optional[str]
    metrics_json: Optional[str]

    class Config:
        from_attributes = True


class HydrationRunItemOut(BaseModel):
    id: int
    run_id: int
    workspace_source_id: int
    document_id: Optional[int]
    source_document_id: str
    action: RunItemAction
    status: RunItemStatus
    error_message: Optional[str]
    duration_ms: Optional[int]
    details_json: Optional[str]

    class Config:
        from_attributes = True


class HydrationAlertOut(BaseModel):
    id: int
    workspace_id: str
    severity: AlertSeverity
    category: AlertCategory
    message: str
    run_id: Optional[int]
    is_active: bool
    created_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]

    class Config:
        from_attributes = True


class RunNowRequest(BaseModel):
    workspace_id: str
    source_ids: Optional[List[int]] = None
    force_full_scan: bool = False
    max_files: Optional[int] = None
    dry_run: bool = False


class DocumentOut(BaseModel):
    id: int
    workspace_id: str
    source_type: SourceType
    source_document_id: str
    source_path: str
    name: str
    mime_type: Optional[str]
    size_bytes: Optional[int]
    modified_time: Optional[datetime]
    checksum: Optional[str]
    doc_type: DocumentType

    model_config = ConfigDict(from_attributes=True)
