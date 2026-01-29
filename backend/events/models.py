"""SQLAlchemy models for event sourcing."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, JSON, String, func

from backend.backend.db import Base


class EventLog(Base):
    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    stream = Column(String, nullable=False)
    stream_entry_id = Column(String, nullable=True)
    event_type = Column(String, nullable=False, index=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    actor_id = Column(Integer, nullable=True)
    correlation_id = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EventOffset(Base):
    __tablename__ = "event_offsets"

    id = Column(Integer, primary_key=True)
    stream = Column(String, unique=True, nullable=False)
    group_name = Column(String, nullable=False)
    last_entry_id = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkspaceStateProjection(Base):
    __tablename__ = "workspace_state_projection"

    workspace_id = Column(Integer, primary_key=True)
    last_hydration_at = Column(DateTime(timezone=True), nullable=True)
    last_hydration_job_id = Column(String, nullable=True)
    last_learning_export_at = Column(DateTime(timezone=True), nullable=True)
    last_promotion_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
