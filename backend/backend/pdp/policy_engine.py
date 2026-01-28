"""Core policy evaluation engine for PDP system."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from .schemas import PolicyRequest, PolicyDecision, PolicyType
from .models import Policy, PolicyDecisionLog
from .rules import (
    RoleBasedRule,
    ProjectAccessRule,
    DataClassificationRule,
    TimeBasedRule,
    ContentProhibitionRule,
    RateLimitRule,
    GeofenceRule
)
from .acl_manager import ACLManager
from .rate_limiter import RateLimiter
from .content_scanner import ContentScanner
from .audit_logger import AuditLogger


class PolicyEngine:
    """
    Core policy evaluation engine that orchestrates policy checks.
    
    Evaluation order (fail-fast):
    1. Rate limiting
    2. Content scanning
    3. Role-based access control (RBAC)
    4. Project access control (ACL)
    5. Data classification
    6. Temporal rules
    """
    
    def __init__(self, db: Session):
        """
        Initialize PolicyEngine.
        
        Args:
            db: Database session
        """
        self.db = db
        self.policies: List[Policy] = []
        self.acl_manager = ACLManager(db)
        self.rate_limiter = RateLimiter(db)
        self.content_scanner = ContentScanner()
        self.audit_logger = AuditLogger(db)
        self.load_policies()
    
    def load_policies(self) -> None:
        """Load active policies from database, ordered by priority."""
        self.policies = (
            self.db.query(Policy)
            .filter(Policy.enabled == True)
            .order_by(Policy.priority.desc())
            .all()
        )
    
    def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        """
        Evaluate a policy request through the complete policy chain.
        
        Args:
            request: Policy request containing user, action, resource, and context
            
        Returns:
            PolicyDecision with allowed status, reason, and conditions
        """
        try:
            # Policy evaluation order (fail-fast)
            
            # 1. Rate limiting - check first to prevent abuse
            rate_limit_result = self.check_rate_limit(request)
            if not rate_limit_result.allowed:
                self._log_decision(request, rate_limit_result)
                return rate_limit_result
            
            # 2. Content scanning - check for malicious content
            content_result = self.check_content(request)
            if not content_result.allowed:
                self._log_decision(request, content_result)
                return content_result
            
            # 3. Access control - check permissions
            access_result = self.check_access(request)
            if not access_result.allowed:
                self._log_decision(request, access_result)
                return access_result
            
            # 4. Apply policy chain - additional policies
            chain_result = self.apply_policy_chain(request)
            self._log_decision(request, chain_result)
            return chain_result
            
        except Exception as e:
            decision = PolicyDecision(
                allowed=False,
                reason=f"Policy evaluation error: {str(e)}",
                audit_required=True
            )
            self._log_decision(request, decision)
            return decision
    
    def check_access(self, request: PolicyRequest) -> PolicyDecision:
        """
        Check access control (RBAC + ACL).
        
        Args:
            request: Policy request
            
        Returns:
            PolicyDecision for access control
        """
        # Check role-based access
        rbac_rule = RoleBasedRule()
        rbac_allowed, rbac_reason = rbac_rule.evaluate(request, self.db)
        
        if not rbac_allowed:
            return PolicyDecision(
                allowed=False,
                reason=f"RBAC denied: {rbac_reason}",
                audit_required=True
            )
        
        # Check project access if project_id in context
        if request.context.get("project_id"):
            project_rule = ProjectAccessRule()
            project_allowed, project_reason = project_rule.evaluate(request, self.db)
            
            if not project_allowed:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Project access denied: {project_reason}",
                    audit_required=True
                )
        
        return PolicyDecision(
            allowed=True,
            reason="Access granted",
            audit_required=True
        )
    
    def check_rate_limit(self, request: PolicyRequest) -> PolicyDecision:
        """
        Check rate limits for the request.
        
        Args:
            request: Policy request
            
        Returns:
            PolicyDecision for rate limiting
        """
        endpoint = request.context.get("endpoint", request.resource_type)
        
        is_allowed, remaining = self.rate_limiter.check_limit(
            request.user_id,
            endpoint
        )
        
        if not is_allowed:
            return PolicyDecision(
                allowed=False,
                reason=f"Rate limit exceeded for endpoint '{endpoint}'",
                audit_required=True
            )
        
        # Increment the counter
        self.rate_limiter.increment(request.user_id, endpoint)
        
        return PolicyDecision(
            allowed=True,
            reason=f"Rate limit OK ({remaining} remaining)",
            audit_required=False
        )
    
    def check_content(self, request: PolicyRequest) -> PolicyDecision:
        """
        Scan content for prohibited patterns.
        
        Args:
            request: Policy request
            
        Returns:
            PolicyDecision for content scanning
        """
        content = request.context.get("content")
        
        if not content:
            return PolicyDecision(
                allowed=True,
                reason="No content to scan",
                audit_required=False
            )
        
        scan_result = self.content_scanner.scan(content)
        
        if not scan_result.safe:
            return PolicyDecision(
                allowed=False,
                reason=f"Content violations detected: {', '.join(scan_result.violations)}",
                conditions=[f"severity={scan_result.severity.value}"],
                audit_required=True
            )
        
        return PolicyDecision(
            allowed=True,
            reason="Content scan passed",
            audit_required=False
        )
    
    def apply_policy_chain(self, request: PolicyRequest) -> PolicyDecision:
        """
        Apply additional policy rules in order.
        
        Args:
            request: Policy request
            
        Returns:
            Final PolicyDecision after all policies
        """
        conditions = []
        
        # Data classification check
        classification_rule = DataClassificationRule()
        classification_allowed, classification_reason = classification_rule.evaluate(request, self.db)
        
        if not classification_allowed:
            return PolicyDecision(
                allowed=False,
                reason=f"Data classification check failed: {classification_reason}",
                audit_required=True
            )
        
        conditions.append(classification_reason)
        
        # Temporal access check
        time_rule = TimeBasedRule()
        time_allowed, time_reason = time_rule.evaluate(request, self.db)
        
        if not time_allowed:
            return PolicyDecision(
                allowed=False,
                reason=f"Temporal check failed: {time_reason}",
                audit_required=True
            )
        
        conditions.append(time_reason)
        
        # Geofencing check (if IP provided)
        if request.context.get("ip_address"):
            geo_rule = GeofenceRule()
            geo_allowed, geo_reason = geo_rule.evaluate(request, self.db)
            
            if not geo_allowed:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Geofence check failed: {geo_reason}",
                    audit_required=True
                )
            
            conditions.append(geo_reason)
        
        # All checks passed
        return PolicyDecision(
            allowed=True,
            reason="All policy checks passed",
            conditions=conditions,
            audit_required=True
        )
    
    def _log_decision(self, request: PolicyRequest, decision: PolicyDecision) -> None:
        """
        Log policy decision to audit trail.
        
        Args:
            request: Policy request
            decision: Policy decision
        """
        if decision.audit_required:
            self.audit_logger.log_decision(
                user_id=request.user_id,
                action=request.action,
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                decision="allow" if decision.allowed else "deny",
                metadata={
                    "reason": decision.reason,
                    "conditions": decision.conditions,
                    "context": request.context
                },
                ip_address=request.context.get("ip_address")
            )
