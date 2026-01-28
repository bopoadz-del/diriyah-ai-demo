"""SQLAlchemy models for nightly hydration pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from backend.backend.db import Base


class SourceType(str, Enum):
    GOOGLE_DRIVE = "google_drive"
    SERVER_FS = "server_fs"


class HydrationStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class DocumentType(str, Enum):
    BOQ = "boq"
    SPEC = "spec"
    CONTRACT = "contract"
    DRAWING = "drawing"
    REPORT = "report"
    OTHER = "other"


class IngestionStatus(str, Enum):
    NEW = "new"
    EXTRACTED = "extracted"
    INDEXED = "indexed"
    LINKED = "linked"
    FAILED = "failed"
    SKIPPED = "skipped"


class VersionStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class HydrationTrigger(str, Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    API = "api"
    RECOVERY = "recovery"


class HydrationRunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class RunItemAction(str, Enum):
    SKIP = "skip"
    NEW = "new"
    UPDATE = "update"
    DELETE = "delete"


class RunItemStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    EXTRACTED = "extracted"
    INDEXED = "indexed"
    LINKED = "linked"
    FAILED = "failed"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class AlertCategory(str, Enum):
    AUTH = "auth"
    EXTRACTION = "extraction"
    INDEXING = "indexing"
    ULE = "ule"
    QUOTA = "quota"
    SYSTEM = "system"


class WorkspaceSource(Base):
    __tablename__ = "workspace_sources"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    source_type = Column(SqlEnum(SourceType), nullable=False)
    name = Column(String, nullable=False)
    config_json = Column(Text, nullable=False)
    secrets_ref = Column(String, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    state = relationship("HydrationState", back_populates="source", uselist=False)


class HydrationState(Base):
    __tablename__ = "hydration_state"

    id = Column(Integer, primary_key=True)
    workspace_source_id = Column(Integer, ForeignKey("workspace_sources.id"), nullable=False, unique=True)
    cursor_json = Column(Text, nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(SqlEnum(HydrationStatus), default=HydrationStatus.IDLE, nullable=False)
    last_error = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0)

    source = relationship("WorkspaceSource", back_populates="state")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    source_type = Column(SqlEnum(SourceType), nullable=False)
    source_document_id = Column(String, nullable=False)
    source_path = Column(String, nullable=False)
    name = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    modified_time = Column(DateTime(timezone=True), nullable=True)
    checksum = Column(Text, nullable=True)
    doc_type = Column(SqlEnum(DocumentType), default=DocumentType.OTHER, nullable=False)
    ingestion_status = Column(SqlEnum(IngestionStatus), default=IngestionStatus.NEW, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    versions = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_num")

    __table_args__ = (
        UniqueConstraint("workspace_id", "source_type", "source_document_id", name="uq_documents_source"),
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    version_num = Column(Integer, nullable=False)
    modified_time = Column(DateTime(timezone=True), nullable=True)
    checksum = Column(Text, nullable=True)
    raw_blob_path = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    extracted_json = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    embedding_status = Column(SqlEnum(VersionStatus), default=VersionStatus.PENDING)
    index_status = Column(SqlEnum(VersionStatus), default=VersionStatus.PENDING)
    ule_status = Column(SqlEnum(VersionStatus), default=VersionStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("document_id", "version_num", name="uq_document_versions"),
    )


class HydrationRun(Base):
    __tablename__ = "hydration_runs"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    trigger = Column(SqlEnum(HydrationTrigger), nullable=False)
    status = Column(SqlEnum(HydrationRunStatus), default=HydrationRunStatus.RUNNING, nullable=False)
    sources_count = Column(Integer, default=0)
    files_seen = Column(Integer, default=0)
    files_new = Column(Integer, default=0)
    files_updated = Column(Integer, default=0)
    files_downloaded = Column(Integer, default=0)
    files_extracted = Column(Integer, default=0)
    files_indexed = Column(Integer, default=0)
    files_ule_processed = Column(Integer, default=0)
    files_failed = Column(Integer, default=0)
    error_summary = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)

    items = relationship("HydrationRunItem", back_populates="run")


class HydrationRunItem(Base):
    __tablename__ = "hydration_run_items"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("hydration_runs.id"), nullable=False, index=True)
    workspace_source_id = Column(Integer, ForeignKey("workspace_sources.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    source_document_id = Column(Text, nullable=False)
    action = Column(SqlEnum(RunItemAction), nullable=False)
    status = Column(SqlEnum(RunItemStatus), default=RunItemStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    details_json = Column(Text, nullable=True)

    run = relationship("HydrationRun", back_populates="items")


class HydrationAlert(Base):
    __tablename__ = "hydration_alerts"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    severity = Column(SqlEnum(AlertSeverity), nullable=False)
    category = Column(SqlEnum(AlertCategory), nullable=False)
    message = Column(Text, nullable=False)
    run_id = Column(Integer, ForeignKey("hydration_runs.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String, nullable=True)


class HydrationLock(Base):
    __tablename__ = "hydration_locks"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=False, unique=True, index=True)
    locked_until = Column(DateTime(timezone=True), nullable=False)
    owner = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
