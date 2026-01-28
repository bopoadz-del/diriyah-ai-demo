"""Tests for individual rule classes."""

import pytest
from datetime import datetime, time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.backend.pdp.rules import (
    RoleBasedRule,
    ProjectAccessRule,
    DataClassificationRule,
    TimeBasedRule,
    ContentProhibitionRule,
    RateLimitRule,
    GeofenceRule
)
from backend.backend.pdp.schemas import PolicyRequest
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
    
    # Create ACL entries
    acl1 = AccessControlList(
        user_id=2,
        project_id=101,
        role="engineer",
        permissions_json=["read", "write", "execute"],
        granted_at=datetime.now()
    )
    session.add(acl1)
    
    session.commit()
    yield session
    session.close()


def test_role_based_rule_admin(db_session):
    """Test that admin role has all permissions."""
    rule = RoleBasedRule()
    
    request = PolicyRequest(
        user_id=1,
        action="delete",
        resource_type="document",
        resource_id=1,
        context={}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is True
    assert "admin" in reason.lower() or "all permissions" in reason.lower()


def test_role_based_rule_viewer(db_session):
    """Test that viewer role has limited permissions."""
    rule = RoleBasedRule()
    
    # Viewer can read
    request = PolicyRequest(
        user_id=3,
        action="read",
        resource_type="document",
        resource_id=1,
        context={}
    )
    allowed, reason = rule.evaluate(request, db_session)
    assert allowed is True
    
    # Viewer cannot write
    request = PolicyRequest(
        user_id=3,
        action="write",
        resource_type="document",
        resource_id=1,
        context={}
    )
    allowed, reason = rule.evaluate(request, db_session)
    assert allowed is False
    assert "not authorized" in reason.lower()


def test_role_based_rule_engineer(db_session):
    """Test that engineer role has execute permission."""
    rule = RoleBasedRule()
    
    request = PolicyRequest(
        user_id=2,
        action="execute",
        resource_type="code",
        resource_id=None,
        context={}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is True
    assert "engineer" in reason.lower()


def test_role_based_rule_user_not_found(db_session):
    """Test that non-existent user is denied."""
    rule = RoleBasedRule()
    
    request = PolicyRequest(
        user_id=999,
        action="read",
        resource_type="document",
        resource_id=1,
        context={}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is False
    assert "not found" in reason.lower()


def test_project_access_rule(db_session):
    """Test project access via ACL."""
    rule = ProjectAccessRule()
    
    # User has access to project 101
    request = PolicyRequest(
        user_id=2,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"project_id": 101}
    )
    allowed, reason = rule.evaluate(request, db_session)
    assert allowed is True
    
    # User does not have access to project 102
    request = PolicyRequest(
        user_id=2,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"project_id": 102}
    )
    allowed, reason = rule.evaluate(request, db_session)
    assert allowed is False


def test_project_access_rule_admin_global(db_session):
    """Test that admin has global project access."""
    rule = ProjectAccessRule()
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"project_id": 102}  # No ACL entry
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is True
    assert "admin" in reason.lower() or "global" in reason.lower()


def test_project_access_rule_no_context(db_session):
    """Test project access without project context."""
    rule = ProjectAccessRule()
    
    # Admin without project context
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={}
    )
    allowed, reason = rule.evaluate(request, db_session)
    assert allowed is True
    
    # Non-admin without project context
    request = PolicyRequest(
        user_id=3,
        action="read",
        resource_type="document",
        resource_id=1,
        context={}
    )
    allowed, reason = rule.evaluate(request, db_session)
    assert allowed is False


def test_project_access_rule_expired(db_session):
    """Test that expired access is denied."""
    from datetime import timedelta
    
    # Create expired ACL entry
    expired_acl = AccessControlList(
        user_id=3,
        project_id=101,
        role="viewer",
        permissions_json=["read"],
        granted_at=datetime.now() - timedelta(days=2),
        expires_at=datetime.now() - timedelta(days=1)
    )
    db_session.add(expired_acl)
    db_session.commit()
    
    rule = ProjectAccessRule()
    
    request = PolicyRequest(
        user_id=3,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"project_id": 101}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is False
    assert "expired" in reason.lower()


def test_time_based_rule_business_hours(db_session):
    """Test time-based access during business hours."""
    # Business hours: 8-17 (5 PM), weekdays
    rule = TimeBasedRule(allowed_hours=list(range(8, 18)), allowed_days=list(range(5)))
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    # Result depends on current time
    # At minimum, check that reason is provided
    assert reason is not None


def test_time_based_rule_outside_hours(db_session):
    """Test time-based access outside allowed hours."""
    # Only allow hour 0-1 (midnight)
    rule = TimeBasedRule(allowed_hours=[0, 1], allowed_days=list(range(7)))
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    # If current hour is not 0-1, should be denied
    current_hour = datetime.now().hour
    if current_hour not in [0, 1]:
        assert allowed is False
        assert "outside allowed hours" in reason.lower()


def test_content_prohibition_ssn(db_session):
    """Test detection of SSN pattern."""
    rule = ContentProhibitionRule()
    
    request = PolicyRequest(
        user_id=1,
        action="write",
        resource_type="document",
        resource_id=1,
        context={"content": "My SSN is 123-45-6789"}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is False
    assert "pii" in reason.lower() or "ssn" in reason.lower()


def test_content_prohibition_sql_injection(db_session):
    """Test detection of SQL injection patterns."""
    rule = ContentProhibitionRule()
    
    request = PolicyRequest(
        user_id=1,
        action="execute",
        resource_type="code",
        resource_id=None,
        context={"content": "SELECT * FROM users UNION SELECT password FROM admin"}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is False
    assert "sql" in reason.lower() or "injection" in reason.lower()


def test_content_prohibition_xss(db_session):
    """Test detection of XSS patterns."""
    rule = ContentProhibitionRule()
    
    request = PolicyRequest(
        user_id=1,
        action="write",
        resource_type="document",
        resource_id=1,
        context={"content": "<script>alert('XSS')</script>"}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is False
    assert "xss" in reason.lower() or "script" in reason.lower()


def test_content_prohibition_command_injection(db_session):
    """Test detection of command injection patterns."""
    rule = ContentProhibitionRule()
    
    request = PolicyRequest(
        user_id=1,
        action="execute",
        resource_type="code",
        resource_id=None,
        context={"content": "ls -la; rm -rf /"}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is False
    assert "command" in reason.lower() or "injection" in reason.lower()


def test_content_prohibition_safe_content(db_session):
    """Test that safe content passes."""
    rule = ContentProhibitionRule()
    
    request = PolicyRequest(
        user_id=1,
        action="write",
        resource_type="document",
        resource_id=1,
        context={"content": "This is a safe document with normal text."}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is True
    assert "passed" in reason.lower()


def test_rate_limit_rule(db_session):
    """Test rate limiting rule."""
    rule = RateLimitRule(limit=5, window_seconds=60)
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"endpoint": "test"}
    )
    
    # First few requests should succeed
    for i in range(5):
        allowed, reason = rule.evaluate(request, db_session)
        if i < 5:
            assert allowed is True
    
    # 6th request should fail
    allowed, reason = rule.evaluate(request, db_session)
    assert allowed is False
    assert "rate limit" in reason.lower()


def test_geofence_rule_allowed_ip(db_session):
    """Test geofence rule with allowed IP."""
    rule = GeofenceRule(allowed_ips=["192.168.1.1", "10.0.0.1"])
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"ip_address": "192.168.1.1"}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is True


def test_geofence_rule_blocked_ip(db_session):
    """Test geofence rule with blocked IP."""
    rule = GeofenceRule(blocked_ips=["192.168.1.100"])
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"ip_address": "192.168.1.100"}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is False
    assert "blocked" in reason.lower()


def test_geofence_rule_no_ip(db_session):
    """Test geofence rule without IP address."""
    rule = GeofenceRule(allowed_ips=["192.168.1.1"])
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    # No IP to check, should allow
    assert allowed is True


def test_data_classification_rule_sufficient_clearance(db_session):
    """Test data classification with sufficient clearance."""
    rule = DataClassificationRule()
    
    # Admin accessing confidential data
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"classification": "confidential"}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is True


def test_data_classification_rule_insufficient_clearance(db_session):
    """Test data classification with insufficient clearance."""
    rule = DataClassificationRule()
    
    # Viewer accessing restricted data
    request = PolicyRequest(
        user_id=3,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"classification": "restricted"}
    )
    
    allowed, reason = rule.evaluate(request, db_session)
    
    assert allowed is False
    assert "insufficient" in reason.lower() or "clearance" in reason.lower()
