"""SQLAlchemy models for PDP system."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, func
from sqlalchemy.orm import relationship
from backend.backend.db import Base


class Policy(Base):
    """Policy definitions for access control."""
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    policy_type = Column(String, nullable=False)  # rbac, abac, content, rate_limit, data_classification, temporal
    rules_json = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PolicyDecisionLog(Base):
    """Log of policy decisions."""
    __tablename__ = "policy_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)
    decision = Column(String, nullable=False)  # allow or deny
    reason = Column(Text, nullable=True)
    context_json = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class AccessControlList(Base):
    """User access control lists for projects."""
    __tablename__ = "access_control_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    role = Column(String, nullable=False)  # admin, director, engineer, commercial, safety_officer, viewer
    permissions_json = Column(JSON, nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)


class RateLimit(Base):
    """Rate limit tracking per user and endpoint."""
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String, nullable=False)
    limit_count = Column(Integer, nullable=False)
    window_seconds = Column(Integer, nullable=False)
    current_count = Column(Integer, default=0)
    window_start = Column(DateTime(timezone=True), server_default=func.now())


class ProhibitedPattern(Base):
    """Patterns to detect in content scanning."""
    __tablename__ = "prohibited_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(String, nullable=False)  # pii, sql_injection, xss, command_injection
    pattern_regex = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # low, medium, high, critical
    enabled = Column(Boolean, default=True)
    description = Column(Text, nullable=True)


class PDPAuditLog(Base):
    """Comprehensive audit log for PDP decisions."""
    __tablename__ = "pdp_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(Integer, nullable=True)
    decision = Column(String, nullable=False)  # allow or deny
    metadata_json = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
