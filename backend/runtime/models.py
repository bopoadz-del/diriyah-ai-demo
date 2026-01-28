"""SQLAlchemy models for the Self-Coding Runtime System."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    func,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

try:
    from backend.backend.db import Base
except ImportError:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()


class CodeExecution(Base):
    """Record of a code execution request and result."""

    __tablename__ = "code_executions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    query = Column(Text, nullable=False)
    generated_code = Column(Text, nullable=False)
    result_json = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, success, error
    execution_time = Column(Float, nullable=True)  # seconds
    memory_used = Column(Integer, nullable=True)  # bytes
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    logs = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan")


class ApprovedFunctionModel(Base):
    """Registry of approved analytical functions."""

    __tablename__ = "approved_functions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    signature = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=False, default="low")  # low, medium, high
    enabled = Column(Boolean, default=True)
    max_runtime = Column(Float, default=5.0)  # seconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ExecutionLog(Base):
    """Log entries for code executions."""

    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("code_executions.id"), nullable=False)
    log_level = Column(String(20), nullable=False, default="INFO")  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    execution = relationship("CodeExecution", back_populates="logs")
