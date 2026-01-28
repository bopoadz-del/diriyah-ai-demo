"""Tests for ACLManager class."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.backend.pdp.acl_manager import ACLManager, ROLE_PERMISSIONS
from backend.backend.pdp.schemas import Role
from backend.backend.pdp.models import AccessControlList
from backend.backend.models import Base, User, Project


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create test users
    admin_user = User(id=1, name="Admin User", email="admin@test.com", role="admin")
    engineer_user = User(id=2, name="Engineer User", email="engineer@test.com", role="engineer")
    viewer_user = User(id=3, name="Viewer User", email="viewer@test.com", role="viewer")
    director_user = User(id=4, name="Director User", email="director@test.com", role="director")
    session.add_all([admin_user, engineer_user, viewer_user, director_user])
    
    # Create test projects (Project model doesn't have description field)
    project1 = Project(id=101, name="Test Project 1")
    project2 = Project(id=102, name="Test Project 2")
    session.add_all([project1, project2])
    
    session.commit()
    yield session
    session.close()


def test_grant_access(db_session):
    """Test granting access to a user."""
    manager = ACLManager(db_session)
    
    acl_entry = manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.ENGINEER,
        granted_by=1
    )
    
    assert acl_entry.user_id == 2
    assert acl_entry.project_id == 101
    assert acl_entry.role == Role.ENGINEER
    assert "read" in acl_entry.permissions
    assert "write" in acl_entry.permissions
    assert "execute" in acl_entry.permissions
    assert acl_entry.granted_by == 1


def test_grant_access_update_existing(db_session):
    """Test updating existing access grant."""
    manager = ACLManager(db_session)
    
    # Grant initial access
    manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.VIEWER,
        granted_by=1
    )
    
    # Update to engineer
    acl_entry = manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.ENGINEER,
        granted_by=1
    )
    
    assert acl_entry.role == Role.ENGINEER
    assert "execute" in acl_entry.permissions
    
    # Verify only one ACL entry exists
    acls = db_session.query(AccessControlList).filter(
        AccessControlList.user_id == 2,
        AccessControlList.project_id == 101
    ).all()
    assert len(acls) == 1


def test_grant_access_invalid_user(db_session):
    """Test granting access to non-existent user."""
    manager = ACLManager(db_session)
    
    with pytest.raises(ValueError, match="User.*not found"):
        manager.grant_access(
            user_id=999,
            project_id=101,
            role=Role.VIEWER,
            granted_by=1
        )


def test_grant_access_invalid_project(db_session):
    """Test granting access to non-existent project."""
    manager = ACLManager(db_session)
    
    with pytest.raises(ValueError, match="Project.*not found"):
        manager.grant_access(
            user_id=2,
            project_id=999,
            role=Role.VIEWER,
            granted_by=1
        )


def test_grant_access_with_expiration(db_session):
    """Test granting access with expiration date."""
    manager = ACLManager(db_session)
    
    expires_at = datetime.now() + timedelta(days=30)
    
    acl_entry = manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.ENGINEER,
        granted_by=1,
        expires_at=expires_at
    )
    
    assert acl_entry.expires_at is not None
    assert acl_entry.expires_at == expires_at


def test_revoke_access(db_session):
    """Test revoking user access."""
    manager = ACLManager(db_session)
    
    # Grant access first
    manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.ENGINEER,
        granted_by=1
    )
    
    # Revoke access
    result = manager.revoke_access(user_id=2, project_id=101)
    
    assert result is True
    
    # Verify ACL entry is deleted
    acl = db_session.query(AccessControlList).filter(
        AccessControlList.user_id == 2,
        AccessControlList.project_id == 101
    ).first()
    assert acl is None


def test_revoke_access_nonexistent(db_session):
    """Test revoking non-existent access."""
    manager = ACLManager(db_session)
    
    result = manager.revoke_access(user_id=2, project_id=101)
    
    assert result is False


def test_check_permission_allowed(db_session):
    """Test checking allowed permission."""
    manager = ACLManager(db_session)
    
    # Grant access
    manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.ENGINEER,
        granted_by=1
    )
    
    # Check permissions
    assert manager.check_permission(2, 101, "read") is True
    assert manager.check_permission(2, 101, "write") is True
    assert manager.check_permission(2, 101, "execute") is True


def test_check_permission_denied(db_session):
    """Test checking denied permission."""
    manager = ACLManager(db_session)
    
    # Grant viewer access
    manager.grant_access(
        user_id=3,
        project_id=101,
        role=Role.VIEWER,
        granted_by=1
    )
    
    # Viewer can read but not write
    assert manager.check_permission(3, 101, "read") is True
    assert manager.check_permission(3, 101, "write") is False
    assert manager.check_permission(3, 101, "delete") is False


def test_check_permission_admin_global(db_session):
    """Test that admin has global permissions."""
    manager = ACLManager(db_session)
    
    # Admin user (id=1) has no ACL entry but should have permissions
    assert manager.check_permission(1, 101, "read") is True
    assert manager.check_permission(1, 101, "write") is True
    assert manager.check_permission(1, 101, "delete") is True
    assert manager.check_permission(1, 101, "admin") is True


def test_check_permission_admin_overrides(db_session):
    """Test that admin permission grants all permissions."""
    manager = ACLManager(db_session)
    
    # Grant admin role
    manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.ADMIN,
        granted_by=1
    )
    
    # Admin permission should grant all
    assert manager.check_permission(2, 101, "read") is True
    assert manager.check_permission(2, 101, "write") is True
    assert manager.check_permission(2, 101, "delete") is True
    assert manager.check_permission(2, 101, "anything") is True


def test_list_user_projects(db_session):
    """Test listing projects accessible to a user."""
    manager = ACLManager(db_session)
    
    # Grant access to multiple projects
    manager.grant_access(user_id=2, project_id=101, role=Role.ENGINEER, granted_by=1)
    manager.grant_access(user_id=2, project_id=102, role=Role.VIEWER, granted_by=1)
    
    projects = manager.list_user_projects(user_id=2)
    
    assert len(projects) == 2
    project_ids = [p["project_id"] for p in projects]
    assert 101 in project_ids
    assert 102 in project_ids


def test_list_user_projects_admin(db_session):
    """Test that admin sees all projects."""
    manager = ACLManager(db_session)
    
    # Admin should see all projects even without ACL entries
    projects = manager.list_user_projects(user_id=1)
    
    assert len(projects) >= 2  # At least the two test projects
    project_ids = [p["project_id"] for p in projects]
    assert 101 in project_ids
    assert 102 in project_ids


def test_list_user_projects_no_access(db_session):
    """Test listing projects for user with no access."""
    manager = ACLManager(db_session)
    
    projects = manager.list_user_projects(user_id=3)
    
    # Viewer with no ACL entries should have empty list
    assert len(projects) == 0


def test_expired_access(db_session):
    """Test that expired access is not returned."""
    manager = ACLManager(db_session)
    
    # Grant expired access
    expires_at = datetime.now() - timedelta(days=1)
    manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.ENGINEER,
        granted_by=1,
        expires_at=expires_at
    )
    
    # Expired access should not be listed
    projects = manager.list_user_projects(user_id=2)
    assert len(projects) == 0
    
    # Expired access should deny permissions
    permissions = manager.get_user_permissions(user_id=2, project_id=101)
    assert len(permissions) == 0
    
    assert manager.check_permission(2, 101, "read") is False


def test_get_user_permissions(db_session):
    """Test getting user permissions for a project."""
    manager = ACLManager(db_session)
    
    manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.ENGINEER,
        granted_by=1
    )
    
    permissions = manager.get_user_permissions(user_id=2, project_id=101)
    
    assert "read" in permissions
    assert "write" in permissions
    assert "execute" in permissions
    assert "delete" not in permissions


def test_update_permissions(db_session):
    """Test updating custom permissions."""
    manager = ACLManager(db_session)
    
    # Grant initial access
    manager.grant_access(
        user_id=2,
        project_id=101,
        role=Role.ENGINEER,
        granted_by=1
    )
    
    # Update to custom permissions
    custom_permissions = ["read", "write"]
    acl_entry = manager.update_permissions(
        user_id=2,
        project_id=101,
        permissions=custom_permissions
    )
    
    assert acl_entry is not None
    assert set(acl_entry.permissions) == set(custom_permissions)


def test_update_permissions_nonexistent(db_session):
    """Test updating permissions for non-existent ACL."""
    manager = ACLManager(db_session)
    
    result = manager.update_permissions(
        user_id=2,
        project_id=101,
        permissions=["read"]
    )
    
    assert result is None


def test_list_project_users(db_session):
    """Test listing users with access to a project."""
    manager = ACLManager(db_session)
    
    # Grant access to multiple users
    manager.grant_access(user_id=2, project_id=101, role=Role.ENGINEER, granted_by=1)
    manager.grant_access(user_id=3, project_id=101, role=Role.VIEWER, granted_by=1)
    
    users = manager.list_project_users(project_id=101)
    
    # Should include granted users plus admin (global access)
    assert len(users) >= 2
    user_ids = [u["user_id"] for u in users]
    assert 2 in user_ids
    assert 3 in user_ids


def test_list_project_users_includes_admin(db_session):
    """Test that admins are included in project user list."""
    manager = ACLManager(db_session)
    
    users = manager.list_project_users(project_id=101)
    
    # Admin should be included even without ACL entry
    user_ids = [u["user_id"] for u in users]
    assert 1 in user_ids  # Admin user
    
    # Find admin user
    admin_user = next(u for u in users if u["user_id"] == 1)
    assert "admin" in admin_user["permissions"]


def test_role_permissions_mapping(db_session):
    """Test that role permissions are correctly mapped."""
    manager = ACLManager(db_session)
    
    # Test each role
    manager.grant_access(user_id=2, project_id=101, role=Role.ADMIN, granted_by=1)
    admin_perms = manager.get_user_permissions(2, 101)
    assert "admin" in admin_perms
    assert "delete" in admin_perms
    
    manager.grant_access(user_id=2, project_id=101, role=Role.DIRECTOR, granted_by=1)
    director_perms = manager.get_user_permissions(2, 101)
    assert "export" in director_perms
    assert "admin" not in director_perms
    
    manager.grant_access(user_id=2, project_id=101, role=Role.VIEWER, granted_by=1)
    viewer_perms = manager.get_user_permissions(2, 101)
    assert "read" in viewer_perms
    assert len(viewer_perms) == 1
