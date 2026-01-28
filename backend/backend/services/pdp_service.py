"""Business logic wrapper for PDP system operations."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, time
from sqlalchemy.orm import Session

from backend.backend.pdp.policy_engine import PolicyEngine
from backend.backend.pdp.schemas import PolicyRequest, PolicyDecision, Role
from backend.backend.pdp.acl_manager import ACLManager
from backend.backend.pdp.rate_limiter import RateLimiter
from backend.backend.pdp.content_scanner import ContentScanner
from backend.backend.pdp.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


# Data classification levels
class DataClassification:
    """Data classification levels for access control."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


# User clearance levels (maps to roles)
CLEARANCE_LEVELS = {
    Role.ADMIN: 4,
    Role.DIRECTOR: 3,
    Role.ENGINEER: 2,
    Role.COMMERCIAL: 2,
    Role.SAFETY_OFFICER: 2,
    Role.VIEWER: 1,
}


# Data classification required clearance
CLASSIFICATION_CLEARANCE = {
    DataClassification.PUBLIC: 1,
    DataClassification.INTERNAL: 2,
    DataClassification.CONFIDENTIAL: 3,
    DataClassification.RESTRICTED: 4,
}


class PDPService:
    """
    High-level service for PDP operations.
    
    Provides business logic wrappers for common PDP operations including:
    - Document access control
    - Project access control
    - Code execution permissions
    - Export permissions
    - Resource classification
    - User clearance checks
    - Business hours validation
    """
    
    def __init__(self, db: Session):
        """
        Initialize PDPService.
        
        Args:
            db: Database session
        """
        self.db = db
        self.engine = PolicyEngine(db)
        self.acl_manager = ACLManager(db)
        self.rate_limiter = RateLimiter(db)
        self.content_scanner = ContentScanner(db)
        self.audit_logger = AuditLogger(db)
    
    def check_document_access(
        self,
        user_id: int,
        document_id: int,
        action: str = "read",
        project_id: Optional[int] = None
    ) -> PolicyDecision:
        """
        Check if user has access to a document.
        
        Args:
            user_id: User ID
            document_id: Document ID
            action: Action to perform (read, write, delete, export)
            project_id: Optional project ID that document belongs to
            
        Returns:
            PolicyDecision with allowed status and reason
        """
        try:
            # Get document classification
            classification = self.get_resource_classification("document", document_id)
            
            # Get user clearance
            clearance = self.get_user_clearance(user_id, project_id)
            
            # Build policy request
            request = PolicyRequest(
                user_id=user_id,
                action=action,
                resource_type="document",
                resource_id=document_id,
                context={
                    "classification": classification,
                    "clearance": clearance,
                    "project_id": project_id,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            
            return self.log_and_evaluate(request)
        
        except Exception as e:
            logger.error(f"Error checking document access: {str(e)}", exc_info=True)
            return PolicyDecision(
                allowed=False,
                reason=f"Error checking access: {str(e)}",
                audit_required=True
            )
    
    def check_project_access(
        self,
        user_id: int,
        project_id: int,
        action: str = "read"
    ) -> PolicyDecision:
        """
        Check if user has access to a project.
        
        Args:
            user_id: User ID
            project_id: Project ID
            action: Action to perform (read, write, delete, admin)
            
        Returns:
            PolicyDecision with allowed status and reason
        """
        try:
            # Check ACL for project access
            has_access = self.acl_manager.check_permission(user_id, project_id, action)
            
            if not has_access:
                return PolicyDecision(
                    allowed=False,
                    reason=f"User does not have {action} permission on project {project_id}",
                    audit_required=True
                )
            
            # Build policy request
            request = PolicyRequest(
                user_id=user_id,
                action=action,
                resource_type="project",
                resource_id=project_id,
                context={
                    "project_id": project_id,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            
            return self.log_and_evaluate(request)
        
        except Exception as e:
            logger.error(f"Error checking project access: {str(e)}", exc_info=True)
            return PolicyDecision(
                allowed=False,
                reason=f"Error checking access: {str(e)}",
                audit_required=True
            )
    
    def check_code_execution_permission(
        self,
        user_id: int,
        code: str,
        project_id: Optional[int] = None
    ) -> PolicyDecision:
        """
        Check if user can execute code (with content scanning).
        
        Args:
            user_id: User ID
            code: Code to execute
            project_id: Optional project ID
            
        Returns:
            PolicyDecision with allowed status and reason
        """
        try:
            # Scan code for malicious content
            scan_result = self.content_scanner.scan(code)
            
            if not scan_result.safe:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Code contains prohibited patterns: {', '.join(scan_result.violations)}",
                    conditions=scan_result.violations,
                    audit_required=True
                )
            
            # Check rate limit for code execution
            allowed, remaining = self.rate_limiter.check_limit(user_id, "execute")
            if not allowed:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Rate limit exceeded for code execution",
                    audit_required=True
                )
            
            # Build policy request
            request = PolicyRequest(
                user_id=user_id,
                action="execute",
                resource_type="code",
                resource_id=None,
                context={
                    "project_id": project_id,
                    "code_length": len(code),
                    "scan_result": scan_result.dict(),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            
            return self.log_and_evaluate(request)
        
        except Exception as e:
            logger.error(f"Error checking code execution permission: {str(e)}", exc_info=True)
            return PolicyDecision(
                allowed=False,
                reason=f"Error checking permission: {str(e)}",
                audit_required=True
            )
    
    def check_export_permission(
        self,
        user_id: int,
        resource_type: str,
        resource_id: int,
        export_format: str = "pdf",
        project_id: Optional[int] = None
    ) -> PolicyDecision:
        """
        Check if user can export a resource.
        
        Args:
            user_id: User ID
            resource_type: Type of resource to export
            resource_id: Resource ID
            export_format: Export format (pdf, csv, xlsx, etc.)
            project_id: Optional project ID
            
        Returns:
            PolicyDecision with allowed status and reason
        """
        try:
            # Check rate limit for exports
            allowed, remaining = self.rate_limiter.check_limit(user_id, "export")
            if not allowed:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Rate limit exceeded for exports",
                    audit_required=True
                )
            
            # Get resource classification
            classification = self.get_resource_classification(resource_type, resource_id)
            
            # Get user clearance
            clearance = self.get_user_clearance(user_id, project_id)
            
            # Check if user has sufficient clearance for classification
            required_clearance = CLASSIFICATION_CLEARANCE.get(
                classification,
                CLASSIFICATION_CLEARANCE[DataClassification.INTERNAL]
            )
            
            if clearance < required_clearance:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Insufficient clearance to export {classification} data",
                    audit_required=True
                )
            
            # Build policy request
            request = PolicyRequest(
                user_id=user_id,
                action="export",
                resource_type=resource_type,
                resource_id=resource_id,
                context={
                    "export_format": export_format,
                    "classification": classification,
                    "clearance": clearance,
                    "project_id": project_id,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            
            return self.log_and_evaluate(request)
        
        except Exception as e:
            logger.error(f"Error checking export permission: {str(e)}", exc_info=True)
            return PolicyDecision(
                allowed=False,
                reason=f"Error checking permission: {str(e)}",
                audit_required=True
            )
    
    def log_and_evaluate(self, request: PolicyRequest) -> PolicyDecision:
        """
        Evaluate policy request and log the decision.
        
        Args:
            request: Policy request
            
        Returns:
            Policy decision
        """
        try:
            # Evaluate policy
            decision = self.engine.evaluate(request)
            
            # Log decision
            self.audit_logger.log_decision(
                user_id=request.user_id,
                action=request.action,
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                decision="allow" if decision.allowed else "deny",
                metadata={
                    "reason": decision.reason,
                    "conditions": decision.conditions,
                    "context": request.context,
                }
            )
            
            return decision
        
        except Exception as e:
            logger.error(f"Error evaluating policy: {str(e)}", exc_info=True)
            return PolicyDecision(
                allowed=False,
                reason=f"Policy evaluation error: {str(e)}",
                audit_required=True
            )
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def get_resource_classification(
        self,
        resource_type: str,
        resource_id: int
    ) -> str:
        """
        Get data classification level for a resource.
        
        In a real implementation, this would query the database for the
        resource's classification level. For now, returns a default.
        
        Args:
            resource_type: Type of resource
            resource_id: Resource ID
            
        Returns:
            Classification level (public, internal, confidential, restricted)
        """
        # TODO: Implement actual classification lookup from database
        # For now, return a default based on resource type
        
        if resource_type in ["document", "project"]:
            return DataClassification.INTERNAL
        elif resource_type in ["code", "export"]:
            return DataClassification.CONFIDENTIAL
        else:
            return DataClassification.INTERNAL
    
    def get_user_clearance(
        self,
        user_id: int,
        project_id: Optional[int] = None
    ) -> int:
        """
        Get user's clearance level.
        
        Args:
            user_id: User ID
            project_id: Optional project ID to check project-specific role
            
        Returns:
            Clearance level (1-4)
        """
        try:
            if project_id:
                # Get user's permissions on specific project
                permissions = self.acl_manager.get_user_permissions(user_id, project_id)
                if permissions:
                    # Infer role from permissions
                    if "admin" in permissions:
                        return CLEARANCE_LEVELS.get(Role.ADMIN, 1)
                    elif "export" in permissions and "execute" in permissions:
                        return CLEARANCE_LEVELS.get(Role.DIRECTOR, 1)
                    elif "execute" in permissions:
                        return CLEARANCE_LEVELS.get(Role.ENGINEER, 1)
                    elif "write" in permissions:
                        return CLEARANCE_LEVELS.get(Role.COMMERCIAL, 1)
                    else:
                        return CLEARANCE_LEVELS.get(Role.VIEWER, 1)
            
            # Get user's highest role across all projects
            projects = self.acl_manager.list_user_projects(user_id)
            if projects:
                max_clearance = 1
                for project in projects:
                    role = project.get("role", "viewer")
                    try:
                        role_enum = Role(role)
                        clearance = CLEARANCE_LEVELS.get(role_enum, 1)
                        max_clearance = max(max_clearance, clearance)
                    except ValueError:
                        continue
                return max_clearance
            
            # Default clearance for users without any ACL entries
            return 1
        
        except Exception as e:
            logger.error(f"Error getting user clearance: {str(e)}", exc_info=True)
            return 1
    
    def is_business_hours(self, timestamp: Optional[datetime] = None) -> bool:
        """
        Check if timestamp is within business hours.
        
        Business hours: Monday-Friday, 8:00 AM - 6:00 PM
        
        Args:
            timestamp: Optional timestamp to check (defaults to now)
            
        Returns:
            True if within business hours
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Check if weekday (Monday=0, Sunday=6)
        if timestamp.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check if within 8 AM - 6 PM
        business_start = time(8, 0)
        business_end = time(18, 0)
        current_time = timestamp.time()
        
        return business_start <= current_time <= business_end
    
    def validate_business_hours_access(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        require_business_hours: bool = False
    ) -> PolicyDecision:
        """
        Validate if action can be performed based on business hours policy.
        
        Args:
            user_id: User ID
            action: Action to perform
            resource_type: Resource type
            require_business_hours: Whether to enforce business hours
            
        Returns:
            PolicyDecision with allowed status
        """
        if require_business_hours and not self.is_business_hours():
            return PolicyDecision(
                allowed=False,
                reason="Action not allowed outside business hours",
                conditions=["business_hours"],
                audit_required=True
            )
        
        return PolicyDecision(
            allowed=True,
            reason="Business hours validation passed",
            audit_required=False
        )
