"""SQLAlchemy models for background jobs and job events."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    func,
)

from backend.backend.db import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True, nullable=False, index=True)
    redis_stream = Column(String, nullable=False, default="jobs:main")
    redis_entry_id = Column(String, nullable=True)
    job_type = Column(String, nullable=False, index=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    status = Column(String, nullable=False, default="queued", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    result_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class BackgroundJobEvent(Base):
    __tablename__ = "background_job_events"

    id = Column(Integer, primary_key=True)
    job_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    message = Column(Text, nullable=True)
    data_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
