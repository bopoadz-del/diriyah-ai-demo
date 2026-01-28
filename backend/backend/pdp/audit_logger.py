"""Audit logging for PDP decisions and access events."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import PDPAuditLog
from .schemas import AuditLog
from backend.backend.models import User


class AuditLogger:
    """
    Manages audit logging for policy decisions and access events.
    """
    
    def __init__(self, db: Session):
        """
        Initialize AuditLogger.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def log_decision(
        self,
        user_id: Optional[int],
        action: str,
        resource_type: Optional[str],
        resource_id: Optional[int],
        decision: str,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """
        Log a policy decision.
        
        Args:
            user_id: User ID making the request
            action: Action being performed
            resource_type: Type of resource being accessed
            resource_id: ID of resource being accessed
            decision: Decision result ("allow" or "deny")
            metadata: Additional metadata about the decision
            ip_address: IP address of the request
            
        Returns:
            AuditLog entry
        """
        audit_entry = PDPAuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            decision=decision,
            metadata_json=metadata or {},
            ip_address=ip_address,
            timestamp=datetime.now()
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return AuditLog(
            id=audit_entry.id,
            user_id=audit_entry.user_id,
            action=audit_entry.action,
            resource_type=audit_entry.resource_type,
            resource_id=audit_entry.resource_id,
            decision=audit_entry.decision,
            timestamp=audit_entry.timestamp,
            metadata=audit_entry.metadata_json,
            ip_address=audit_entry.ip_address
        )
    
    def log_access(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        success: bool = True,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log an access event.
        
        Args:
            user_id: User ID
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource ID
            success: Whether access was successful
            ip_address: IP address
            metadata: Additional metadata
            
        Returns:
            AuditLog entry
        """
        decision = "allow" if success else "deny"
        
        return self.log_decision(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            decision=decision,
            metadata=metadata,
            ip_address=ip_address
        )
    
    def get_audit_trail(
        self,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        action: Optional[str] = None,
        decision: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Get audit trail with filters.
        
        Args:
            user_id: Filter by user ID
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            action: Filter by action
            decision: Filter by decision (allow/deny)
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of AuditLog entries
        """
        query = self.db.query(PDPAuditLog)
        
        # Apply filters
        if user_id is not None:
            query = query.filter(PDPAuditLog.user_id == user_id)
        
        if resource_type:
            query = query.filter(PDPAuditLog.resource_type == resource_type)
        
        if resource_id is not None:
            query = query.filter(PDPAuditLog.resource_id == resource_id)
        
        if action:
            query = query.filter(PDPAuditLog.action == action)
        
        if decision:
            query = query.filter(PDPAuditLog.decision == decision)
        
        if start_date:
            query = query.filter(PDPAuditLog.timestamp >= start_date)
        
        if end_date:
            query = query.filter(PDPAuditLog.timestamp <= end_date)
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(desc(PDPAuditLog.timestamp))
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        results = query.all()
        
        # Convert to schema
        audit_logs = []
        for entry in results:
            audit_logs.append(AuditLog(
                id=entry.id,
                user_id=entry.user_id,
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                decision=entry.decision,
                timestamp=entry.timestamp,
                metadata=entry.metadata_json,
                ip_address=entry.ip_address
            ))
        
        return audit_logs
    
    def get_denied_attempts(
        self,
        user_id: Optional[int] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get denied access attempts within time window.
        
        Args:
            user_id: Filter by user ID (None for all users)
            hours: Time window in hours
            limit: Maximum number of results
            
        Returns:
            List of AuditLog entries for denied attempts
        """
        start_date = datetime.now() - timedelta(hours=hours)
        
        return self.get_audit_trail(
            user_id=user_id,
            decision="deny",
            start_date=start_date,
            limit=limit
        )
    
    def get_user_activity(
        self,
        user_id: int,
        days: int = 7,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get user activity for the past N days.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            limit: Maximum number of results
            
        Returns:
            List of AuditLog entries for user
        """
        start_date = datetime.now() - timedelta(days=days)
        
        return self.get_audit_trail(
            user_id=user_id,
            start_date=start_date,
            limit=limit
        )
    
    def get_resource_access_history(
        self,
        resource_type: str,
        resource_id: int,
        days: int = 30,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get access history for a specific resource.
        
        Args:
            resource_type: Type of resource
            resource_id: Resource ID
            days: Number of days to look back
            limit: Maximum number of results
            
        Returns:
            List of AuditLog entries for resource
        """
        start_date = datetime.now() - timedelta(days=days)
        
        return self.get_audit_trail(
            resource_type=resource_type,
            resource_id=resource_id,
            start_date=start_date,
            limit=limit
        )
    
    def export_audit_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export audit logs for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            format: Export format (json, csv)
            
        Returns:
            Dict with audit log data and metadata
        """
        logs = self.get_audit_trail(
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for export
        )
        
        # Get user details for enrichment
        user_ids = set(log.user_id for log in logs if log.user_id)
        users = self.db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {user.id: {"name": user.name, "email": user.email} for user in users}
        
        # Enrich logs with user info
        enriched_logs = []
        for log in logs:
            log_dict = {
                "id": log.id,
                "user_id": log.user_id,
                "user_name": user_map.get(log.user_id, {}).get("name"),
                "user_email": user_map.get(log.user_id, {}).get("email"),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "decision": log.decision,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "ip_address": log.ip_address,
                "metadata": log.metadata
            }
            enriched_logs.append(log_dict)
        
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_entries": len(enriched_logs),
            "format": format,
            "logs": enriched_logs
        }
    
    def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dict with statistics
        """
        query = self.db.query(PDPAuditLog)
        
        if start_date:
            query = query.filter(PDPAuditLog.timestamp >= start_date)
        
        if end_date:
            query = query.filter(PDPAuditLog.timestamp <= end_date)
        
        all_logs = query.all()
        
        # Calculate statistics
        total_requests = len(all_logs)
        allowed_requests = sum(1 for log in all_logs if log.decision == "allow")
        denied_requests = sum(1 for log in all_logs if log.decision == "deny")
        
        # Top users
        user_counts = {}
        for log in all_logs:
            if log.user_id:
                user_counts[log.user_id] = user_counts.get(log.user_id, 0) + 1
        
        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Top actions
        action_counts = {}
        for log in all_logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        top_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Top resources
        resource_counts = {}
        for log in all_logs:
            if log.resource_type:
                key = f"{log.resource_type}:{log.resource_id}" if log.resource_id else log.resource_type
                resource_counts[key] = resource_counts.get(key, 0) + 1
        
        top_resources = sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "total_requests": total_requests,
            "allowed_requests": allowed_requests,
            "denied_requests": denied_requests,
            "denial_rate": (denied_requests / total_requests * 100) if total_requests > 0 else 0,
            "top_users": [{"user_id": uid, "count": count} for uid, count in top_users],
            "top_actions": [{"action": action, "count": count} for action, count in top_actions],
            "top_resources": [{"resource": res, "count": count} for res, count in top_resources]
        }
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Delete audit logs older than specified days.
        
        Args:
            days: Delete logs older than this many days
            
        Returns:
            Number of logs deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted_count = self.db.query(PDPAuditLog).filter(
            PDPAuditLog.timestamp < cutoff_date
        ).delete()
        
        self.db.commit()
        return deleted_count
