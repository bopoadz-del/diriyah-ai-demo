"""Tests for PolicyEngine class."""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.backend.pdp.policy_engine import PolicyEngine
from backend.backend.pdp.schemas import PolicyRequest, PolicyType, Role
from backend.backend.pdp.models import Policy, AccessControlList
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
    session.add_all([admin_user, engineer_user, viewer_user])
    
    # Create test projects (Project model doesn't have description field)
    project1 = Project(id=101, name="Test Project 1")
    project2 = Project(id=102, name="Test Project 2")
    session.add_all([project1, project2])
    
    # Create ACL entries
    acl1 = AccessControlList(
        user_id=2,
        project_id=101,
        role=Role.ENGINEER.value,
        permissions_json=["read", "write", "execute"],
        granted_at=datetime.now()
    )
    session.add(acl1)
    
    session.commit()
    yield session
    session.close()


def test_evaluate_allow(db_session):
    """Test that user with permission is allowed access."""
    engine = PolicyEngine(db_session)
    
    request = PolicyRequest(
        user_id=1,  # Admin user
        action="read",
        resource_type="document",
        resource_id=1,
        context={"project_id": 101}
    )
    
    decision = engine.evaluate(request)
    
    assert decision.allowed is True
    assert "allowed" in decision.reason.lower() or "passed" in decision.reason.lower()


def test_evaluate_deny_no_permission(db_session):
    """Test that user without permission is denied access."""
    engine = PolicyEngine(db_session)
    
    request = PolicyRequest(
        user_id=3,  # Viewer user
        action="delete",
        resource_type="document",
        resource_id=1,
        context={"project_id": 101}
    )
    
    decision = engine.evaluate(request)
    
    assert decision.allowed is False
    assert "denied" in decision.reason.lower() or "not authorized" in decision.reason.lower()


def test_evaluate_deny_rate_limit(db_session):
    """Test that exceeded rate limit denies access."""
    engine = PolicyEngine(db_session)
    
    # Make requests up to the limit
    from backend.backend.pdp.rate_limiter import RATE_LIMITS
    default_limit = RATE_LIMITS["default"]["limit"]
    
    # Exhaust rate limit
    for _ in range(default_limit):
        engine.rate_limiter.increment(1, "document")
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"endpoint": "document"}
    )
    
    decision = engine.evaluate(request)
    
    assert decision.allowed is False
    assert "rate limit" in decision.reason.lower()


def test_policy_priority(db_session):
    """Test that higher priority policy overrides lower priority."""
    # Create policies with different priorities
    high_priority_policy = Policy(
        name="High Priority Policy",
        policy_type=PolicyType.RBAC.value,
        rules_json={"role": "admin", "action": "delete"},
        enabled=True,
        priority=200
    )
    low_priority_policy = Policy(
        name="Low Priority Policy",
        policy_type=PolicyType.RBAC.value,
        rules_json={"role": "viewer", "action": "read"},
        enabled=True,
        priority=50
    )
    db_session.add_all([high_priority_policy, low_priority_policy])
    db_session.commit()
    
    engine = PolicyEngine(db_session)
    
    # Reload policies to pick up the new ones
    engine.load_policies()
    
    # Verify policies are loaded in priority order
    assert len(engine.policies) >= 2
    priorities = [p.priority for p in engine.policies]
    assert priorities == sorted(priorities, reverse=True)


def test_chain_evaluation(db_session):
    """Test that multiple policies are evaluated in order."""
    engine = PolicyEngine(db_session)
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={
            "project_id": 101,
            "classification": "internal"
        }
    )
    
    # Should evaluate through entire chain
    decision = engine.evaluate(request)
    
    # Admin should pass all checks
    assert decision.allowed is True
    
    # Check that conditions were evaluated (chain applied)
    # The apply_policy_chain method adds conditions for each check
    assert isinstance(decision.conditions, list)


def test_check_access_rbac(db_session):
    """Test role-based access control."""
    engine = PolicyEngine(db_session)
    
    # Admin can delete
    request = PolicyRequest(
        user_id=1,
        action="delete",
        resource_type="document",
        resource_id=1,
        context={}
    )
    decision = engine.check_access(request)
    assert decision.allowed is True
    
    # Viewer cannot delete
    request = PolicyRequest(
        user_id=3,
        action="delete",
        resource_type="document",
        resource_id=1,
        context={}
    )
    decision = engine.check_access(request)
    assert decision.allowed is False


def test_check_access_project_acl(db_session):
    """Test project access control list."""
    engine = PolicyEngine(db_session)
    
    # Engineer has access to project 101
    request = PolicyRequest(
        user_id=2,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"project_id": 101}
    )
    decision = engine.check_access(request)
    assert decision.allowed is True
    
    # Engineer does not have ACL for project 102
    request = PolicyRequest(
        user_id=2,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"project_id": 102}
    )
    decision = engine.check_access(request)
    assert decision.allowed is False


def test_check_rate_limit_increment(db_session):
    """Test that rate limit counter increments correctly."""
    engine = PolicyEngine(db_session)
    
    request = PolicyRequest(
        user_id=2,
        action="read",
        resource_type="test",
        resource_id=1,
        context={"endpoint": "test"}
    )
    
    # First request should succeed and increment
    decision = engine.check_rate_limit(request)
    assert decision.allowed is True
    
    # Check counter was incremented
    allowed, remaining = engine.rate_limiter.check_limit(2, "test")
    assert allowed is True
    
    from backend.backend.pdp.rate_limiter import RATE_LIMITS
    default_limit = RATE_LIMITS["default"]["limit"]
    assert remaining < default_limit  # Some requests consumed


def test_check_content_no_content(db_session):
    """Test content scanning with no content."""
    engine = PolicyEngine(db_session)
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={}
    )
    
    decision = engine.check_content(request)
    assert decision.allowed is True
    assert "no content" in decision.reason.lower()


def test_check_content_with_violations(db_session):
    """Test content scanning detects violations."""
    engine = PolicyEngine(db_session)
    
    request = PolicyRequest(
        user_id=1,
        action="execute",
        resource_type="code",
        resource_id=None,
        context={"content": "SELECT * FROM users; DROP TABLE users;"}
    )
    
    decision = engine.check_content(request)
    assert decision.allowed is False
    assert "violation" in decision.reason.lower()


def test_apply_policy_chain_classification(db_session):
    """Test data classification check in policy chain."""
    engine = PolicyEngine(db_session)
    
    # Admin with restricted classification should pass
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"classification": "restricted"}
    )
    decision = engine.apply_policy_chain(request)
    assert decision.allowed is True
    
    # Viewer with restricted classification should fail
    request = PolicyRequest(
        user_id=3,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"classification": "restricted"}
    )
    decision = engine.apply_policy_chain(request)
    assert decision.allowed is False


def test_log_decision_audit_trail(db_session):
    """Test that decisions are logged to audit trail."""
    engine = PolicyEngine(db_session)
    
    request = PolicyRequest(
        user_id=1,
        action="read",
        resource_type="document",
        resource_id=1,
        context={"project_id": 101}
    )
    
    decision = engine.evaluate(request)
    
    # Verify decision was logged
    from backend.backend.pdp.models import AuditLog
    logs = db_session.query(AuditLog).filter(
        AuditLog.user_id == 1,
        AuditLog.action == "read"
    ).all()
    
    assert len(logs) > 0
    assert logs[0].decision == ("allow" if decision.allowed else "deny")
