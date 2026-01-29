"""SQLAlchemy models for event sourcing."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from backend.backend.db import Base


class EventLog(Base):
    __tablename__ = "event_log"

    event_id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False, index=True)
    ts = Column(String, nullable=False)
    workspace_id = Column(Integer, nullable=True, index=True)
    actor_id = Column(Integer, nullable=True)
    correlation_id = Column(String, nullable=True)
    source = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EventOffset(Base):
    __tablename__ = "event_offsets"

    id = Column(Integer, primary_key=True)
    stream_name = Column(String, nullable=False, index=True)
    consumer_group = Column(String, nullable=False, index=True)
    last_id = Column(String, nullable=False, default="0-0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkspaceStateProjection(Base):
    __tablename__ = "workspace_state_projection"

    workspace_id = Column(Integer, primary_key=True)
    last_hydration_at = Column(DateTime(timezone=True), nullable=True)
    last_hydration_job_id = Column(String, nullable=True)
    last_learning_export_at = Column(DateTime(timezone=True), nullable=True)
    last_promotion_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
