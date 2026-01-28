"""Rule classes for policy evaluation."""

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Tuple
from sqlalchemy.orm import Session

from .schemas import PolicyRequest
from backend.backend.models import User, Project


class BaseRule(ABC):
    """Abstract base class for policy rules."""

    @abstractmethod
    def evaluate(self, request: PolicyRequest, db: Session) -> Tuple[bool, str]:
        """
        Evaluate the rule.
        
        Returns:
            Tuple[bool, str]: (allowed, reason)
        """
        pass


class RoleBasedRule(BaseRule):
    """Check user role permissions."""

    # Role-based action mappings
    ROLE_ACTIONS = {
        "admin": ["*"],  # All actions
        "director": ["read", "write", "execute", "export"],
        "engineer": ["read", "write", "execute"],
        "commercial": ["read", "write", "export"],
        "safety_officer": ["read", "write"],
        "viewer": ["read"],
    }

    def __init__(self, required_role: str = None, allowed_actions: list = None):
        self.required_role = required_role
        self.allowed_actions = allowed_actions or []

    def evaluate(self, request: PolicyRequest, db: Session) -> Tuple[bool, str]:
        """Check if user role has permission for action."""
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            return False, "User not found"

        user_role = user.role or "viewer"
        action = request.action.lower()

        # Check if role allows all actions
        if "*" in self.ROLE_ACTIONS.get(user_role, []):
            return True, f"Role '{user_role}' has all permissions"

        # Check specific role actions
        allowed_actions = self.ROLE_ACTIONS.get(user_role, [])
        if action in allowed_actions or any(action.startswith(a.replace("*", "")) for a in allowed_actions):
            return True, f"Action '{action}' allowed for role '{user_role}'"

        return False, f"Role '{user_role}' not authorized for action '{action}'"


class ProjectAccessRule(BaseRule):
    """Check project membership via ACL."""

    def evaluate(self, request: PolicyRequest, db: Session) -> Tuple[bool, str]:
        """Check if user has access to project."""
        from .models import AccessControlList

        project_id = request.context.get("project_id")
        if not project_id:
            # If no project context, check if user is admin
            user = db.query(User).filter(User.id == request.user_id).first()
            if user and user.role == "admin":
                return True, "Admin has global access"
            return False, "No project context provided"

        # Check ACL
        acl = db.query(AccessControlList).filter(
            AccessControlList.user_id == request.user_id,
            AccessControlList.project_id == project_id
        ).first()

        if acl:
            # Check if access expired
            if acl.expires_at and acl.expires_at < datetime.now():
                return False, "Access expired"
            return True, f"User has '{acl.role}' access to project"

        # Check if user is admin or director (global access)
        user = db.query(User).filter(User.id == request.user_id).first()
        if user and user.role in ["admin", "director"]:
            return True, f"User role '{user.role}' has global access"

        return False, "No access to project"


class DataClassificationRule(BaseRule):
    """Check data sensitivity clearance."""

    CLASSIFICATION_LEVELS = {
        "public": 0,
        "internal": 1,
        "confidential": 2,
        "restricted": 3,
    }

    def __init__(self, required_clearance: str = "internal"):
        self.required_clearance = required_clearance

    def evaluate(self, request: PolicyRequest, db: Session) -> Tuple[bool, str]:
        """Check if user has required clearance level."""
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            return False, "User not found"

        # For now, map roles to clearance levels
        role_clearance = {
            "admin": "restricted",
            "director": "confidential",
            "engineer": "internal",
            "commercial": "internal",
            "safety_officer": "internal",
            "viewer": "public",
        }

        user_clearance = role_clearance.get(user.role, "public")
        resource_classification = request.context.get("classification", "internal")

        user_level = self.CLASSIFICATION_LEVELS.get(user_clearance, 0)
        resource_level = self.CLASSIFICATION_LEVELS.get(resource_classification, 1)

        if user_level >= resource_level:
            return True, f"User clearance '{user_clearance}' sufficient for '{resource_classification}'"

        return False, f"Insufficient clearance: user has '{user_clearance}', resource requires '{resource_classification}'"


class TimeBasedRule(BaseRule):
    """Time-based access control."""

    def __init__(self, allowed_hours: list = None, allowed_days: list = None):
        self.allowed_hours = allowed_hours or list(range(24))  # All hours by default
        self.allowed_days = allowed_days or list(range(7))  # All days by default

    def evaluate(self, request: PolicyRequest, db: Session) -> Tuple[bool, str]:
        """Check if current time is within allowed hours/days."""
        now = datetime.now()
        current_hour = now.hour
        current_day = now.weekday()

        if current_hour not in self.allowed_hours:
            return False, f"Access denied: outside allowed hours (current hour: {current_hour})"

        if current_day not in self.allowed_days:
            return False, f"Access denied: outside allowed days (current day: {current_day})"

        return True, "Within allowed time window"


class ContentProhibitionRule(BaseRule):
    """Scan for prohibited content patterns."""

    PROHIBITED_PATTERNS = {
        "pii_ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "pii_credit_card": r"\b\d{16}\b",
        "pii_password": r"password\s*[:=]\s*\S+",
        "sql_injection": r"(union|select|drop|insert|delete|update).*from",
        "sql_comment": r"--|\#|\/\*",
        "xss_script": r"<script[^>]*>.*?</script>",
        "xss_javascript": r"javascript:",
        "xss_event": r"on\w+\s*=",
        "command_injection": r";\s*(rm|wget|curl|bash|sh)",
    }

    def evaluate(self, request: PolicyRequest, db: Session) -> Tuple[bool, str]:
        """Check for prohibited patterns in content."""
        content = request.context.get("content", "")
        if not content:
            return True, "No content to scan"

        violations = []
        for pattern_name, pattern in self.PROHIBITED_PATTERNS.items():
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(pattern_name)

        if violations:
            return False, f"Prohibited content detected: {', '.join(violations)}"

        return True, "Content scan passed"


class RateLimitRule(BaseRule):
    """Enforce rate limits."""

    def __init__(self, limit: int = 100, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds

    def evaluate(self, request: PolicyRequest, db: Session) -> Tuple[bool, str]:
        """Check rate limit for user and endpoint."""
        from .models import RateLimit

        endpoint = request.context.get("endpoint", request.resource_type)

        # Get or create rate limit record
        rate_limit = db.query(RateLimit).filter(
            RateLimit.user_id == request.user_id,
            RateLimit.endpoint == endpoint
        ).first()

        if not rate_limit:
            # Create new rate limit record
            rate_limit = RateLimit(
                user_id=request.user_id,
                endpoint=endpoint,
                limit_count=self.limit,
                window_seconds=self.window_seconds,
                current_count=1,
                window_start=datetime.now()
            )
            db.add(rate_limit)
            db.commit()
            return True, "Rate limit initialized"

        # Check if window expired
        window_age = (datetime.now() - rate_limit.window_start).total_seconds()
        if window_age > rate_limit.window_seconds:
            # Reset window
            rate_limit.window_start = datetime.now()
            rate_limit.current_count = 1
            db.commit()
            return True, "Rate limit window reset"

        # Check if limit exceeded
        if rate_limit.current_count >= rate_limit.limit_count:
            remaining_time = rate_limit.window_seconds - window_age
            return False, f"Rate limit exceeded. Try again in {int(remaining_time)} seconds"

        # Increment counter
        rate_limit.current_count += 1
        db.commit()
        return True, f"Rate limit OK ({rate_limit.current_count}/{rate_limit.limit_count})"


class GeofenceRule(BaseRule):
    """IP-based location check."""

    def __init__(self, allowed_ips: list = None, blocked_ips: list = None):
        self.allowed_ips = allowed_ips or []
        self.blocked_ips = blocked_ips or []

    def evaluate(self, request: PolicyRequest, db: Session) -> Tuple[bool, str]:
        """Check if request IP is allowed."""
        ip_address = request.context.get("ip_address")
        if not ip_address:
            return True, "No IP address to check"

        # Check blocklist first
        if ip_address in self.blocked_ips:
            return False, f"IP address {ip_address} is blocked"

        # If allowlist exists, check it
        if self.allowed_ips and ip_address not in self.allowed_ips:
            return False, f"IP address {ip_address} not in allowlist"

        return True, "IP address allowed"
