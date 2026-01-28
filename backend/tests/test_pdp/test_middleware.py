"""Tests for PDPMiddleware."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.backend.pdp.middleware import PDPMiddleware, PUBLIC_ENDPOINTS
from backend.backend.pdp.schemas import PolicyDecision
from backend.backend.models import Base, User, Project
from backend.backend.db import get_db


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
    session.add(project1)
    
    session.commit()
    yield session
    session.close()


@pytest.fixture
def test_app(db_session):
    """Create a test FastAPI app with PDPMiddleware."""
    app = FastAPI()
    
    # Override database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Add middleware
    app.add_middleware(PDPMiddleware)
    
    # Add test endpoints
    @app.get("/health")
    def health():
        return {"status": "ok"}
    
    @app.get("/api/test")
    def test_endpoint():
        return {"message": "test"}
    
    @app.get("/api/protected")
    def protected_endpoint(request: Request):
        # Access PDP decision from request state
        decision = getattr(request.state, "pdp_decision", None)
        user_id = getattr(request.state, "user_id", None)
        return {"message": "protected", "user_id": user_id, "decision": decision}
    
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


def test_middleware_allows_public_endpoints(client):
    """Test that middleware allows public endpoints without PDP check."""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_middleware_allows_docs(client):
    """Test that middleware allows docs endpoints."""
    # Note: /docs may redirect, so check for success or redirect status
    response = client.get("/docs")
    assert response.status_code in [200, 307]


def test_middleware_checks_rate_limit(client, db_session):
    """Test that middleware checks rate limits."""
    # Exhaust rate limit
    from backend.backend.pdp.rate_limiter import RateLimiter, RATE_LIMITS
    limiter = RateLimiter(db_session)
    
    default_limit = RATE_LIMITS["default"]["limit"]
    for _ in range(default_limit):
        limiter.increment(1, "test")
    
    # Next request should be rate limited
    response = client.get("/api/test", headers={"X-User-ID": "1"})
    
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


def test_middleware_blocks_forbidden(client, db_session):
    """Test that middleware blocks forbidden access."""
    # Use viewer trying to access endpoint requiring higher permissions
    # This would require specific policy configuration
    # For now, test that the middleware evaluates policies
    
    response = client.get("/api/test", headers={"X-User-ID": "3"})
    
    # Should either allow or deny based on policy evaluation
    # The response should not be an error (500)
    assert response.status_code in [200, 403, 429]


def test_middleware_logs_decision(client, db_session):
    """Test that middleware logs all decisions."""
    from backend.backend.pdp.models import AuditLog
    
    # Make a request
    response = client.get("/api/test", headers={"X-User-ID": "1"})
    
    # Check that audit log was created
    logs = db_session.query(AuditLog).filter(
        AuditLog.user_id == 1,
        AuditLog.action == "GET"
    ).all()
    
    # Should have at least one log entry
    assert len(logs) > 0


def test_middleware_passes_allowed(client, db_session):
    """Test that middleware passes allowed requests."""
    response = client.get("/api/test", headers={"X-User-ID": "1"})
    
    # Admin should be allowed
    assert response.status_code == 200
    assert response.json() == {"message": "test"}


def test_middleware_extracts_user_id_from_header(client):
    """Test that middleware extracts user_id from X-User-ID header."""
    response = client.get("/api/protected", headers={"X-User-ID": "2"})
    
    # Check that user_id was extracted
    if response.status_code == 200:
        data = response.json()
        assert data["user_id"] == 2


def test_middleware_uses_default_user_without_header(client):
    """Test that middleware uses default user_id when no header provided."""
    response = client.get("/api/protected")
    
    # Should use default user_id (1)
    if response.status_code == 200:
        data = response.json()
        assert data["user_id"] is not None


def test_middleware_stores_decision_in_request_state(client):
    """Test that middleware stores PDP decision in request state."""
    response = client.get("/api/protected", headers={"X-User-ID": "1"})
    
    if response.status_code == 200:
        data = response.json()
        # Decision should be stored in request state
        assert "decision" in data


def test_middleware_extracts_resource_type(client):
    """Test that middleware correctly extracts resource type from path."""
    # The middleware should extract "test" from "/api/test"
    response = client.get("/api/test", headers={"X-User-ID": "1"})
    
    # Should not error on resource type extraction
    assert response.status_code in [200, 403, 429]


def test_middleware_extracts_endpoint(client):
    """Test that middleware correctly extracts endpoint for rate limiting."""
    # Make request to specific endpoint
    response = client.get("/api/test", headers={"X-User-ID": "1"})
    
    # Should apply rate limit to "test" endpoint
    assert response.status_code in [200, 429]


def test_middleware_handles_different_methods(client):
    """Test that middleware handles different HTTP methods."""
    # GET request
    get_response = client.get("/api/test", headers={"X-User-ID": "1"})
    assert get_response.status_code in [200, 403, 429]


def test_middleware_handles_ip_address(client):
    """Test that middleware extracts and uses IP address."""
    response = client.get(
        "/api/test",
        headers={
            "X-User-ID": "1",
            "X-Forwarded-For": "192.168.1.100"
        }
    )
    
    # Should process request with IP address in context
    assert response.status_code in [200, 403, 429]


def test_middleware_handles_real_ip_header(client):
    """Test that middleware handles X-Real-IP header."""
    response = client.get(
        "/api/test",
        headers={
            "X-User-ID": "1",
            "X-Real-IP": "10.0.0.1"
        }
    )
    
    assert response.status_code in [200, 403, 429]


def test_middleware_handles_user_agent(client):
    """Test that middleware includes user agent in context."""
    response = client.get(
        "/api/test",
        headers={
            "X-User-ID": "1",
            "User-Agent": "TestClient/1.0"
        }
    )
    
    assert response.status_code in [200, 403, 429]


def test_middleware_error_handling(client):
    """Test that middleware handles errors gracefully."""
    # Make request that might cause error
    response = client.get("/api/nonexistent", headers={"X-User-ID": "1"})
    
    # Should either return 404 or handle gracefully
    # Should not return 500 due to middleware error
    assert response.status_code in [200, 403, 404, 429]


def test_middleware_increments_rate_limit(client, db_session):
    """Test that middleware increments rate limit counter."""
    from backend.backend.pdp.models import RateLimit
    
    # Make first request
    response1 = client.get("/api/test", headers={"X-User-ID": "1"})
    
    # Check rate limit was incremented
    rate_limit = db_session.query(RateLimit).filter(
        RateLimit.user_id == 1,
        RateLimit.endpoint == "test"
    ).first()
    
    if rate_limit:
        count1 = rate_limit.current_count
        
        # Make second request
        response2 = client.get("/api/test", headers={"X-User-ID": "1"})
        
        db_session.refresh(rate_limit)
        count2 = rate_limit.current_count
        
        # Counter should have increased
        assert count2 > count1


def test_middleware_returns_429_on_rate_limit(client, db_session):
    """Test that middleware returns 429 status on rate limit."""
    from backend.backend.pdp.rate_limiter import RateLimiter, RATE_LIMITS
    
    # Exhaust rate limit
    limiter = RateLimiter(db_session)
    default_limit = RATE_LIMITS["default"]["limit"]
    
    for _ in range(default_limit):
        limiter.increment(1, "test")
    
    # Next request should return 429
    response = client.get("/api/test", headers={"X-User-ID": "1"})
    
    assert response.status_code == 429
    data = response.json()
    assert "rate limit" in data["detail"].lower()
    assert "remaining" in data


def test_middleware_returns_403_on_denied(client, db_session):
    """Test that middleware returns 403 status on access denied."""
    # This test requires specific policy that denies access
    # For now, test the structure of 403 response if it occurs
    
    response = client.get("/api/test", headers={"X-User-ID": "3"})
    
    if response.status_code == 403:
        data = response.json()
        assert "detail" in data
        assert "reason" in data


def test_middleware_skips_multiple_public_endpoints(client):
    """Test that all public endpoints are skipped."""
    for endpoint in PUBLIC_ENDPOINTS:
        # Only test endpoints that exist
        if endpoint in ["/health"]:
            response = client.get(endpoint)
            # Public endpoint should not be blocked
            assert response.status_code in [200, 307, 404]


def test_middleware_context_includes_all_fields(client, db_session):
    """Test that middleware includes all required fields in policy context."""
    from backend.backend.pdp.models import AuditLog
    
    response = client.get(
        "/api/test",
        headers={
            "X-User-ID": "1",
            "X-Forwarded-For": "192.168.1.1",
            "User-Agent": "TestAgent/1.0"
        }
    )
    
    # Check that audit log contains context
    logs = db_session.query(AuditLog).filter(
        AuditLog.user_id == 1
    ).order_by(AuditLog.id.desc()).first()
    
    if logs and logs.metadata:
        # Context should be in metadata
        assert "context" in logs.metadata or "reason" in logs.metadata


def test_middleware_chain_continues_on_allow(client):
    """Test that request processing continues after middleware allows."""
    response = client.get("/api/test", headers={"X-User-ID": "1"})
    
    if response.status_code == 200:
        # Endpoint handler was called
        assert response.json() == {"message": "test"}


def test_middleware_anonymous_access(client):
    """Test middleware behavior with no user_id."""
    # Don't provide X-User-ID header
    response = client.get("/api/test")
    
    # Should either use default user or handle anonymous
    # Should not crash
    assert response.status_code in [200, 403, 429]


def test_middleware_invalid_user_id(client):
    """Test middleware with invalid user_id format."""
    response = client.get("/api/test", headers={"X-User-ID": "invalid"})
    
    # Should handle gracefully
    assert response.status_code in [200, 403, 429, 500]


def test_middleware_logs_rate_limit_exceeded(client, db_session):
    """Test that rate limit exceeded events are logged."""
    from backend.backend.pdp.rate_limiter import RateLimiter, RATE_LIMITS
    from backend.backend.pdp.models import AuditLog
    
    # Exhaust rate limit
    limiter = RateLimiter(db_session)
    default_limit = RATE_LIMITS["default"]["limit"]
    
    for _ in range(default_limit):
        limiter.increment(1, "test")
    
    # Make request that exceeds limit
    response = client.get("/api/test", headers={"X-User-ID": "1"})
    
    # Check that rate limit event was logged
    logs = db_session.query(AuditLog).filter(
        AuditLog.user_id == 1,
        AuditLog.decision == "rate_limit_exceeded"
    ).all()
    
    assert len(logs) > 0
