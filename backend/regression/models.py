"""SQLAlchemy models for regression guard and promotion gating."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from backend.backend.db import Base


class PromotionRequest(Base):
    __tablename__ = "promotion_requests"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(String, nullable=True, index=True)
    component = Column(String, nullable=False, index=True)
    baseline_tag = Column(String, nullable=False)
    candidate_tag = Column(String, nullable=False)
    status = Column(String, nullable=False, default="requested")
    requested_by = Column(Integer, nullable=True, index=True)
    approved_by = Column(Integer, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    checks = relationship("RegressionCheck", back_populates="promotion_request", cascade="all, delete-orphan")


class RegressionCheck(Base):
    __tablename__ = "regression_checks"

    id = Column(Integer, primary_key=True)
    promotion_request_id = Column(Integer, ForeignKey("promotion_requests.id"), nullable=False, index=True)
    suite_name = Column(String, nullable=False)
    baseline_run_id = Column(Integer, nullable=True)
    candidate_run_id = Column(Integer, nullable=True)
    baseline_score = Column(Float, nullable=True)
    candidate_score = Column(Float, nullable=True)
    min_threshold = Column(Float, nullable=False)
    max_drop = Column(Float, nullable=False, default=0.02)
    drop_value = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=False, default=False)
    report_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    promotion_request = relationship("PromotionRequest", back_populates="checks")


class RegressionThreshold(Base):
    __tablename__ = "regression_thresholds"

    id = Column(Integer, primary_key=True)
    component = Column(String, unique=True, nullable=False)
    suite_name = Column(String, nullable=False)
    min_threshold = Column(Float, nullable=True)
    max_drop = Column(Float, nullable=False, default=0.02)
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CurrentComponentVersion(Base):
    __tablename__ = "current_component_versions"

    id = Column(Integer, primary_key=True)
    component = Column(String, unique=True, nullable=False)
    current_tag = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
