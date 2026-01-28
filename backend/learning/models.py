"""SQLAlchemy models for learning feedback and dataset exports."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from backend.backend.db import Base


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    event_type = Column(String, nullable=False, index=True)
    event_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    labels = relationship("FeedbackLabel", back_populates="feedback", cascade="all, delete-orphan")
    reviews = relationship("FeedbackReview", back_populates="feedback", cascade="all, delete-orphan")


class FeedbackLabel(Base):
    __tablename__ = "feedback_labels"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback_events.id"), nullable=False, index=True)
    label_type = Column(String, nullable=False, index=True)
    label_value = Column(String, nullable=False)
    labeled_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    feedback = relationship("FeedbackEvent", back_populates="labels")


class FeedbackReview(Base):
    __tablename__ = "feedback_reviews"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback_events.id"), nullable=False, index=True)
    decision = Column(String, nullable=False, index=True)
    reviewer_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    feedback = relationship("FeedbackEvent", back_populates="reviews")


class TrainingDataset(Base):
    __tablename__ = "training_datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    version_tag = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    manifest_json = Column(JSON, nullable=True)
    record_count = Column(Integer, default=0)

    records = relationship(
        "TrainingDatasetRecord",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )


class TrainingDatasetRecord(Base):
    __tablename__ = "training_dataset_records"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("training_datasets.id"), nullable=False, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback_events.id"), nullable=True)
    record_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dataset = relationship("TrainingDataset", back_populates="records")


class LearningRun(Base):
    __tablename__ = "learning_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    dataset_id = Column(Integer, ForeignKey("training_datasets.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    details_json = Column(JSON, nullable=True)


class LearningAlert(Base):
    __tablename__ = "learning_alerts"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String, nullable=True, index=True)
    level = Column(String, nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
