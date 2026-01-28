"""SQLAlchemy models for learning feedback and dataset exports."""

from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from backend.backend.db import Base


class FeedbackReviewStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"


class LearningRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class LearningAlertSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    event_type = Column(String, nullable=True, index=True)
    source = Column(String, nullable=True)
    input_text = Column(Text, nullable=False)
    output_text = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    labels = relationship("FeedbackLabel", back_populates="feedback", cascade="all, delete-orphan")
    reviews = relationship("FeedbackReview", back_populates="feedback", cascade="all, delete-orphan")


class FeedbackLabel(Base):
    __tablename__ = "feedback_labels"

    id = Column(Integer, primary_key=True)
    feedback_id = Column(Integer, ForeignKey("feedback_events.id", ondelete="CASCADE"), nullable=False)
    label_type = Column(String, nullable=False, index=True)
    label_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    feedback = relationship("FeedbackEvent", back_populates="labels")


class FeedbackReview(Base):
    __tablename__ = "feedback_reviews"

    id = Column(Integer, primary_key=True)
    feedback_id = Column(Integer, ForeignKey("feedback_events.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, nullable=True, index=True)
    status = Column(SqlEnum(FeedbackReviewStatus), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    feedback = relationship("FeedbackEvent", back_populates="reviews")


class TrainingDataset(Base):
    __tablename__ = "training_datasets"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    dataset_name = Column(String, nullable=False, index=True)
    version_tag = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="exported")
    manifest_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    records = relationship("TrainingDatasetRecord", back_populates="dataset", cascade="all, delete-orphan")


class TrainingDatasetRecord(Base):
    __tablename__ = "training_dataset_records"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("training_datasets.id", ondelete="CASCADE"), nullable=False)
    feedback_id = Column(Integer, ForeignKey("feedback_events.id", ondelete="SET NULL"), nullable=True)
    record_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dataset = relationship("TrainingDataset", back_populates="records")


class LearningRun(Base):
    __tablename__ = "learning_runs"

    id = Column(Integer, primary_key=True)
    run_type = Column(String, nullable=False)
    status = Column(SqlEnum(LearningRunStatus), nullable=False, default=LearningRunStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_summary = Column(Text, nullable=True)


class LearningAlert(Base):
    __tablename__ = "learning_alerts"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=False, index=True)
    severity = Column(SqlEnum(LearningAlertSeverity), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
