"""SQLAlchemy models for background job tracking."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func, Boolean

from backend.backend.db import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    redis_stream = Column(String, nullable=False, default="jobs:main")
    redis_entry_id = Column(String, nullable=True)
    job_type = Column(String, nullable=False, index=True)
    workspace_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="queued")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    result_json = Column(JSON, nullable=True)
    not_before_at = Column(DateTime(timezone=True), nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    locked_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class BackgroundJobEvent(Base):
    __tablename__ = "background_job_events"

    id = Column(Integer, primary_key=True)
    job_id = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    data_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OpsSchedule(Base):
    __tablename__ = "ops_schedules"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    workspace_id = Column(String, nullable=True, index=True)
    job_type = Column(String, nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
