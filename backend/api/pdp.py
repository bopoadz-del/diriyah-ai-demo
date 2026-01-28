"""API endpoints for PDP (Policy Decision Point) system."""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.backend.pdp.schemas import (
    PolicyRequest,
    PolicyDecision,
    Policy,
    PolicyType,
    ACLEntry,
    Role,
    RateLimitStatus,
    AuditLog,
    ScanResult,
)
from backend.backend.pdp.policy_engine import PolicyEngine
from backend.backend.pdp.acl_manager import ACLManager
from backend.backend.pdp.rate_limiter import RateLimiter
from backend.backend.pdp.content_scanner import ContentScanner
from backend.backend.pdp.audit_logger import AuditLogger
from backend.backend.pdp import models as pdp_models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdp", tags=["PDP"])


# -------------------------------------------------------------------------
# Policy Evaluation Endpoints
# -------------------------------------------------------------------------

@router.post("/evaluate", response_model=PolicyDecision, status_code=status.HTTP_200_OK)
def evaluate_policy(
    request: PolicyRequest,
    db: Session = Depends(get_db)
) -> PolicyDecision:
    """
    Evaluate a policy request through the PDP engine.
    
    Args:
        request: Policy request with user, action, resource, and context
        db: Database session
        
    Returns:
        Policy decision with allowed status and reason
    """
    try:
        engine = PolicyEngine(db)
        decision = engine.evaluate(request)
        return decision
    except Exception as e:
        logger.error(f"Error evaluating policy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy evaluation failed: {str(e)}"
        )


@router.get("/users/{user_id}/permissions", response_model=List[str], status_code=status.HTTP_200_OK)
def get_user_permissions(
    user_id: int,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> List[str]:
    """
    Get permissions for a user, optionally filtered by project.
    
    Args:
        user_id: User ID
        project_id: Optional project ID to filter permissions
        db: Database session
        
    Returns:
        List of permission strings
    """
    try:
        acl_manager = ACLManager(db)
        
        if project_id:
            permissions = acl_manager.get_user_permissions(user_id, project_id)
        else:
            # Get all permissions across all projects
            projects = acl_manager.list_user_projects(user_id)
            permissions = []
            for project in projects:
                permissions.extend(project.get("permissions", []))
            permissions = list(set(permissions))  # Deduplicate
        
        return permissions
    except Exception as e:
        logger.error(f"Error getting user permissions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get permissions: {str(e)}"
        )


# -------------------------------------------------------------------------
# Access Control Endpoints
# -------------------------------------------------------------------------

@router.post("/access/grant", response_model=ACLEntry, status_code=status.HTTP_201_CREATED)
def grant_access(
    user_id: int,
    project_id: int,
    role: Role,
    granted_by: Optional[int] = None,
    expires_at: Optional[datetime] = None,
    db: Session = Depends(get_db)
) -> ACLEntry:
    """
    Grant user access to a project with specified role.
    
    Args:
        user_id: User ID to grant access
        project_id: Project ID
        role: Role to assign
        granted_by: User ID who granted access
        expires_at: Optional expiration datetime
        db: Database session
        
    Returns:
        ACL entry with granted permissions
    """
    try:
        acl_manager = ACLManager(db)
        entry = acl_manager.grant_access(
            user_id=user_id,
            project_id=project_id,
            role=role,
            granted_by=granted_by,
            expires_at=expires_at
        )
        db.commit()
        return entry
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error granting access: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant access: {str(e)}"
        )


@router.delete("/access/revoke", status_code=status.HTTP_200_OK)
def revoke_access(
    user_id: int,
    project_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Revoke user access to a project.
    
    Args:
        user_id: User ID
        project_id: Project ID
        db: Database session
        
    Returns:
        Success message
    """
    try:
        acl_manager = ACLManager(db)
        success = acl_manager.revoke_access(user_id, project_id)
        db.commit()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No access found for user {user_id} on project {project_id}"
            )
        
        return {"message": "Access revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking access: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke access: {str(e)}"
        )


# -------------------------------------------------------------------------
# Rate Limiting Endpoints
# -------------------------------------------------------------------------

@router.get("/rate-limit/{user_id}/{endpoint}", response_model=RateLimitStatus, status_code=status.HTTP_200_OK)
def check_rate_limit(
    user_id: int,
    endpoint: str,
    db: Session = Depends(get_db)
) -> RateLimitStatus:
    """
    Check rate limit status for a user and endpoint.
    
    Args:
        user_id: User ID
        endpoint: Endpoint identifier
        db: Database session
        
    Returns:
        Rate limit status with remaining requests
    """
    try:
        rate_limiter = RateLimiter(db)
        allowed, remaining = rate_limiter.check_limit(user_id, endpoint)
        
        # Get rate limit configuration
        from backend.backend.pdp.rate_limiter import RATE_LIMITS
        config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
        
        return RateLimitStatus(
            endpoint=endpoint,
            limit=config["limit"],
            remaining=remaining,
            reset_time=int(datetime.now().timestamp()) + config["window_seconds"],
            window_seconds=config["window_seconds"]
        )
    except Exception as e:
        logger.error(f"Error checking rate limit: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check rate limit: {str(e)}"
        )


# -------------------------------------------------------------------------
# Content Scanning Endpoints
# -------------------------------------------------------------------------

@router.post("/scan", response_model=ScanResult, status_code=status.HTTP_200_OK)
def scan_content(
    text: str,
    db: Session = Depends(get_db)
) -> ScanResult:
    """
    Scan text content for prohibited patterns and malicious content.
    
    Args:
        text: Text to scan
        db: Database session
        
    Returns:
        Scan result with violations and sanitized text
    """
    try:
        scanner = ContentScanner(db)
        result = scanner.scan(text)
        return result
    except Exception as e:
        logger.error(f"Error scanning content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content scan failed: {str(e)}"
        )


# -------------------------------------------------------------------------
# Audit Trail Endpoints
# -------------------------------------------------------------------------

@router.get("/audit-trail", response_model=List[AuditLog], status_code=status.HTTP_200_OK)
def get_audit_trail(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
) -> List[AuditLog]:
    """
    Get audit trail with optional filters.
    
    Args:
        user_id: Filter by user ID
        action: Filter by action
        resource_type: Filter by resource type
        start_date: Filter by start date
        end_date: Filter by end date
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of audit log entries
    """
    try:
        audit_logger = AuditLogger(db)
        logs = audit_logger.get_audit_trail(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return logs
    except Exception as e:
        logger.error(f"Error getting audit trail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit trail: {str(e)}"
        )


# -------------------------------------------------------------------------
# Policy Management Endpoints
# -------------------------------------------------------------------------

@router.get("/policies", response_model=List[Policy], status_code=status.HTTP_200_OK)
def list_policies(
    policy_type: Optional[PolicyType] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
) -> List[Policy]:
    """
    List all policies with optional filters.
    
    Args:
        policy_type: Filter by policy type
        enabled: Filter by enabled status
        db: Database session
        
    Returns:
        List of policies
    """
    try:
        query = db.query(pdp_models.Policy)
        
        if policy_type:
            query = query.filter(pdp_models.Policy.policy_type == policy_type.value)
        
        if enabled is not None:
            query = query.filter(pdp_models.Policy.enabled == enabled)
        
        policies = query.order_by(pdp_models.Policy.priority.desc()).all()
        
        # Convert to Pydantic models
        return [
            Policy(
                id=p.id,
                name=p.name,
                policy_type=PolicyType(p.policy_type),
                rules=p.rules_json,
                enabled=p.enabled,
                priority=p.priority,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in policies
        ]
    except Exception as e:
        logger.error(f"Error listing policies: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list policies: {str(e)}"
        )


@router.post("/policies", response_model=Policy, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy: Policy,
    db: Session = Depends(get_db)
) -> Policy:
    """
    Create a new policy.
    
    Args:
        policy: Policy definition
        db: Database session
        
    Returns:
        Created policy with ID
    """
    try:
        db_policy = pdp_models.Policy(
            name=policy.name,
            policy_type=policy.policy_type.value,
            rules_json=policy.rules,
            enabled=policy.enabled,
            priority=policy.priority
        )
        db.add(db_policy)
        db.commit()
        db.refresh(db_policy)
        
        return Policy(
            id=db_policy.id,
            name=db_policy.name,
            policy_type=PolicyType(db_policy.policy_type),
            rules=db_policy.rules_json,
            enabled=db_policy.enabled,
            priority=db_policy.priority,
            created_at=db_policy.created_at,
            updated_at=db_policy.updated_at
        )
    except Exception as e:
        logger.error(f"Error creating policy: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create policy: {str(e)}"
        )


@router.put("/policies/{policy_id}", response_model=Policy, status_code=status.HTTP_200_OK)
def update_policy(
    policy_id: int,
    policy: Policy,
    db: Session = Depends(get_db)
) -> Policy:
    """
    Update an existing policy.
    
    Args:
        policy_id: Policy ID to update
        policy: Updated policy definition
        db: Database session
        
    Returns:
        Updated policy
    """
    try:
        db_policy = db.query(pdp_models.Policy).filter(pdp_models.Policy.id == policy_id).first()
        
        if not db_policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy {policy_id} not found"
            )
        
        db_policy.name = policy.name
        db_policy.policy_type = policy.policy_type.value
        db_policy.rules_json = policy.rules
        db_policy.enabled = policy.enabled
        db_policy.priority = policy.priority
        
        db.commit()
        db.refresh(db_policy)
        
        return Policy(
            id=db_policy.id,
            name=db_policy.name,
            policy_type=PolicyType(db_policy.policy_type),
            rules=db_policy.rules_json,
            enabled=db_policy.enabled,
            priority=db_policy.priority,
            created_at=db_policy.created_at,
            updated_at=db_policy.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating policy: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update policy: {str(e)}"
        )


@router.delete("/policies/{policy_id}", status_code=status.HTTP_200_OK)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Delete a policy.
    
    Args:
        policy_id: Policy ID to delete
        db: Database session
        
    Returns:
        Success message
    """
    try:
        db_policy = db.query(pdp_models.Policy).filter(pdp_models.Policy.id == policy_id).first()
        
        if not db_policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy {policy_id} not found"
            )
        
        db.delete(db_policy)
        db.commit()
        
        return {"message": f"Policy {policy_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting policy: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete policy: {str(e)}"
        )
