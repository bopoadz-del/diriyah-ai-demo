"""Access Control List (ACL) manager for user permissions."""

from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session

from .schemas import Role, ACLEntry
from .models import AccessControlList
from backend.backend.models import User, Project


# Permission constants
PERMISSIONS = [
    "read",
    "write",
    "execute",
    "export",
    "delete",
    "admin",
]

# Role-based permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: ["read", "write", "execute", "export", "delete", "admin"],
    Role.DIRECTOR: ["read", "write", "execute", "export"],
    Role.ENGINEER: ["read", "write", "execute"],
    Role.COMMERCIAL: ["read", "write", "export"],
    Role.SAFETY_OFFICER: ["read", "write"],
    Role.VIEWER: ["read"],
}


class ACLManager:
    """
    Manages access control lists for users and projects.
    """
    
    def __init__(self, db: Session):
        """
        Initialize ACLManager.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def grant_access(
        self,
        user_id: int,
        project_id: int,
        role: Role,
        granted_by: Optional[int] = None,
        expires_at: Optional[datetime] = None
    ) -> ACLEntry:
        """
        Grant user access to a project with a specific role.
        
        Args:
            user_id: User ID to grant access
            project_id: Project ID to grant access to
            role: Role to assign
            granted_by: User ID who granted the access
            expires_at: Optional expiration datetime
            
        Returns:
            ACLEntry with granted permissions
            
        Raises:
            ValueError: If user or project not found
        """
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Validate project exists
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Get permissions for role
        permissions = ROLE_PERMISSIONS.get(role, [])
        
        # Check if ACL entry already exists
        existing_acl = self.db.query(AccessControlList).filter(
            AccessControlList.user_id == user_id,
            AccessControlList.project_id == project_id
        ).first()
        
        if existing_acl:
            # Update existing ACL
            existing_acl.role = role.value
            existing_acl.permissions_json = permissions
            existing_acl.granted_by = granted_by
            existing_acl.granted_at = datetime.now()
            existing_acl.expires_at = expires_at
            self.db.commit()
            self.db.refresh(existing_acl)
            
            return ACLEntry(
                id=existing_acl.id,
                user_id=existing_acl.user_id,
                project_id=existing_acl.project_id,
                role=Role(existing_acl.role),
                permissions=existing_acl.permissions_json,
                granted_by=existing_acl.granted_by,
                granted_at=existing_acl.granted_at,
                expires_at=existing_acl.expires_at
            )
        
        # Create new ACL entry
        new_acl = AccessControlList(
            user_id=user_id,
            project_id=project_id,
            role=role.value,
            permissions_json=permissions,
            granted_by=granted_by,
            granted_at=datetime.now(),
            expires_at=expires_at
        )
        self.db.add(new_acl)
        self.db.commit()
        self.db.refresh(new_acl)
        
        return ACLEntry(
            id=new_acl.id,
            user_id=new_acl.user_id,
            project_id=new_acl.project_id,
            role=Role(new_acl.role),
            permissions=new_acl.permissions_json,
            granted_by=new_acl.granted_by,
            granted_at=new_acl.granted_at,
            expires_at=new_acl.expires_at
        )
    
    def revoke_access(self, user_id: int, project_id: int) -> bool:
        """
        Revoke user access to a project.
        
        Args:
            user_id: User ID
            project_id: Project ID
            
        Returns:
            True if access was revoked, False if no access existed
        """
        acl = self.db.query(AccessControlList).filter(
            AccessControlList.user_id == user_id,
            AccessControlList.project_id == project_id
        ).first()
        
        if acl:
            self.db.delete(acl)
            self.db.commit()
            return True
        
        return False
    
    def get_user_permissions(self, user_id: int, project_id: int) -> List[str]:
        """
        Get list of permissions a user has for a project.
        
        Args:
            user_id: User ID
            project_id: Project ID
            
        Returns:
            List of permission strings
        """
        # Check ACL
        acl = self.db.query(AccessControlList).filter(
            AccessControlList.user_id == user_id,
            AccessControlList.project_id == project_id
        ).first()
        
        if acl:
            # Check if access expired
            if acl.expires_at and acl.expires_at < datetime.now():
                return []
            return acl.permissions_json
        
        # Check if user has global role permissions
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.role in ["admin", "director"]:
            # Global access
            role_enum = Role.ADMIN if user.role == "admin" else Role.DIRECTOR
            return ROLE_PERMISSIONS.get(role_enum, [])
        
        return []
    
    def check_permission(self, user_id: int, project_id: int, permission: str) -> bool:
        """
        Check if a user has a specific permission for a project.
        
        Args:
            user_id: User ID
            project_id: Project ID
            permission: Permission to check (e.g., "read", "write")
            
        Returns:
            True if user has permission, False otherwise
        """
        permissions = self.get_user_permissions(user_id, project_id)
        
        # Check if user has admin permission (grants all)
        if "admin" in permissions:
            return True
        
        return permission in permissions
    
    def list_user_projects(self, user_id: int) -> List[Dict]:
        """
        List all projects a user has access to.
        
        Args:
            user_id: User ID
            
        Returns:
            List of dicts with project info and permissions
        """
        # Get ACL entries for user
        acls = self.db.query(AccessControlList).filter(
            AccessControlList.user_id == user_id
        ).all()
        
        projects = []
        for acl in acls:
            # Skip expired access
            if acl.expires_at and acl.expires_at < datetime.now():
                continue
            
            project = self.db.query(Project).filter(Project.id == acl.project_id).first()
            if project:
                projects.append({
                    "project_id": project.id,
                    "project_name": project.name,
                    "role": acl.role,
                    "permissions": acl.permissions_json,
                    "granted_at": acl.granted_at,
                    "expires_at": acl.expires_at
                })
        
        # Check if user has global role access
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.role in ["admin", "director"]:
            # Add all projects for admin/director
            all_projects = self.db.query(Project).all()
            for project in all_projects:
                # Skip if already in list
                if any(p["project_id"] == project.id for p in projects):
                    continue
                
                role_enum = Role.ADMIN if user.role == "admin" else Role.DIRECTOR
                projects.append({
                    "project_id": project.id,
                    "project_name": project.name,
                    "role": user.role,
                    "permissions": ROLE_PERMISSIONS.get(role_enum, []),
                    "granted_at": None,
                    "expires_at": None
                })
        
        return projects
    
    def list_project_users(self, project_id: int) -> List[Dict]:
        """
        List all users who have access to a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of dicts with user info and permissions
        """
        # Get ACL entries for project
        acls = self.db.query(AccessControlList).filter(
            AccessControlList.project_id == project_id
        ).all()
        
        users = []
        for acl in acls:
            # Skip expired access
            if acl.expires_at and acl.expires_at < datetime.now():
                continue
            
            user = self.db.query(User).filter(User.id == acl.user_id).first()
            if user:
                users.append({
                    "user_id": user.id,
                    "user_name": user.name,
                    "user_email": user.email,
                    "role": acl.role,
                    "permissions": acl.permissions_json,
                    "granted_at": acl.granted_at,
                    "granted_by": acl.granted_by,
                    "expires_at": acl.expires_at
                })
        
        # Add global admins and directors
        global_users = self.db.query(User).filter(
            User.role.in_(["admin", "director"])
        ).all()
        
        for user in global_users:
            # Skip if already in list
            if any(u["user_id"] == user.id for u in users):
                continue
            
            role_enum = Role.ADMIN if user.role == "admin" else Role.DIRECTOR
            users.append({
                "user_id": user.id,
                "user_name": user.name,
                "user_email": user.email,
                "role": user.role,
                "permissions": ROLE_PERMISSIONS.get(role_enum, []),
                "granted_at": None,
                "granted_by": None,
                "expires_at": None
            })
        
        return users
    
    def update_permissions(
        self,
        user_id: int,
        project_id: int,
        permissions: List[str]
    ) -> Optional[ACLEntry]:
        """
        Update custom permissions for a user on a project.
        
        Args:
            user_id: User ID
            project_id: Project ID
            permissions: List of permissions to set
            
        Returns:
            Updated ACLEntry or None if not found
        """
        acl = self.db.query(AccessControlList).filter(
            AccessControlList.user_id == user_id,
            AccessControlList.project_id == project_id
        ).first()
        
        if not acl:
            return None
        
        # Validate permissions
        valid_permissions = [p for p in permissions if p in PERMISSIONS]
        
        acl.permissions_json = valid_permissions
        self.db.commit()
        self.db.refresh(acl)
        
        return ACLEntry(
            id=acl.id,
            user_id=acl.user_id,
            project_id=acl.project_id,
            role=Role(acl.role),
            permissions=acl.permissions_json,
            granted_by=acl.granted_by,
            granted_at=acl.granted_at,
            expires_at=acl.expires_at
        )
