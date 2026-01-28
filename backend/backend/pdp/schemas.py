"""Pydantic schemas for PDP system."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class PolicyType(str, Enum):
    """Policy types."""
    RBAC = "rbac"
    ABAC = "abac"
    CONTENT = "content"
    RATE_LIMIT = "rate_limit"
    DATA_CLASSIFICATION = "data_classification"
    TEMPORAL = "temporal"


class Role(str, Enum):
    """User roles."""
    ADMIN = "admin"
    DIRECTOR = "director"
    ENGINEER = "engineer"
    COMMERCIAL = "commercial"
    SAFETY_OFFICER = "safety_officer"
    VIEWER = "viewer"


class PatternType(str, Enum):
    """Prohibited pattern types."""
    PII = "pii"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"


class Severity(str, Enum):
    """Severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyRequest(BaseModel):
    """Request for policy evaluation."""
    user_id: int
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    """Result of policy evaluation."""
    allowed: bool
    reason: str
    conditions: List[str] = Field(default_factory=list)
    audit_required: bool = True


class Policy(BaseModel):
    """Policy definition."""
    id: Optional[int] = None
    name: str
    policy_type: PolicyType
    rules: Dict[str, Any]
    enabled: bool = True
    priority: int = 100
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ACLEntry(BaseModel):
    """Access control list entry."""
    id: Optional[int] = None
    user_id: int
    project_id: int
    role: Role
    permissions: List[str]
    granted_by: Optional[int] = None
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RateLimitStatus(BaseModel):
    """Rate limit status."""
    endpoint: str
    limit: int
    remaining: int
    reset_time: int
    window_seconds: int = 60


class AuditLog(BaseModel):
    """Audit log entry."""
    id: Optional[int] = None
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    decision: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True


class ProhibitedPattern(BaseModel):
    """Prohibited content pattern."""
    id: Optional[int] = None
    pattern: str
    pattern_type: PatternType
    severity: Severity
    enabled: bool = True
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ScanResult(BaseModel):
    """Content scan result."""
    safe: bool
    violations: List[str] = Field(default_factory=list)
    severity: Severity = Severity.LOW
    sanitized_text: Optional[str] = None
    details: Dict[str, str] = Field(default_factory=dict)
