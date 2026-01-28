"""Tests for RateLimiter class."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time

from backend.backend.pdp.rate_limiter import RateLimiter, RATE_LIMITS
from backend.backend.pdp.models import RateLimit
from backend.backend.models import Base, User


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create test users
    user1 = User(id=1, name="Test User 1", email="user1@test.com", role="engineer")
    user2 = User(id=2, name="Test User 2", email="user2@test.com", role="engineer")
    session.add_all([user1, user2])
    
    session.commit()
    yield session
    session.close()


def test_under_limit(db_session):
    """Test that requests under limit are allowed."""
    limiter = RateLimiter(db_session)
    
    # First request should be allowed
    allowed, remaining = limiter.check_limit(user_id=1, endpoint="test")
    
    assert allowed is True
    assert remaining > 0


def test_at_limit(db_session):
    """Test behavior when reaching the limit."""
    limiter = RateLimiter(db_session)
    
    # Make requests up to the limit
    default_limit = RATE_LIMITS["default"]["limit"]
    
    for i in range(default_limit):
        limiter.increment(user_id=1, endpoint="test")
    
    # Next check should hit limit
    allowed, remaining = limiter.check_limit(user_id=1, endpoint="test")
    
    assert allowed is False
    assert remaining == 0


def test_window_reset(db_session):
    """Test that rate limit resets after window expires."""
    limiter = RateLimiter(db_session)
    
    # Create a rate limit record with expired window
    expired_window = RateLimit(
        user_id=1,
        endpoint="test",
        limit_count=10,
        window_seconds=1,  # 1 second window
        current_count=10,  # At limit
        window_start=datetime.now() - timedelta(seconds=2)  # Expired
    )
    db_session.add(expired_window)
    db_session.commit()
    
    # Check should reset the window
    allowed, remaining = limiter.check_limit(user_id=1, endpoint="test")
    
    assert allowed is True
    assert remaining == 10  # Reset to limit


def test_different_endpoints(db_session):
    """Test that different endpoints have separate limits."""
    limiter = RateLimiter(db_session)
    
    # Exhaust limit for endpoint1
    for i in range(RATE_LIMITS["default"]["limit"]):
        limiter.increment(user_id=1, endpoint="endpoint1")
    
    # endpoint1 should be at limit
    allowed1, remaining1 = limiter.check_limit(user_id=1, endpoint="endpoint1")
    assert allowed1 is False
    
    # endpoint2 should still be available
    allowed2, remaining2 = limiter.check_limit(user_id=1, endpoint="endpoint2")
    assert allowed2 is True
    assert remaining2 > 0


def test_different_users(db_session):
    """Test that different users have separate limits."""
    limiter = RateLimiter(db_session)
    
    # Exhaust limit for user1
    for i in range(RATE_LIMITS["default"]["limit"]):
        limiter.increment(user_id=1, endpoint="test")
    
    # user1 should be at limit
    allowed1, remaining1 = limiter.check_limit(user_id=1, endpoint="test")
    assert allowed1 is False
    
    # user2 should still be available
    allowed2, remaining2 = limiter.check_limit(user_id=2, endpoint="test")
    assert allowed2 is True


def test_increment(db_session):
    """Test incrementing the rate limit counter."""
    limiter = RateLimiter(db_session)
    
    # First increment
    count1 = limiter.increment(user_id=1, endpoint="test")
    assert count1 == 1
    
    # Second increment
    count2 = limiter.increment(user_id=1, endpoint="test")
    assert count2 == 2
    
    # Third increment
    count3 = limiter.increment(user_id=1, endpoint="test")
    assert count3 == 3


def test_increment_creates_record(db_session):
    """Test that increment creates record if it doesn't exist."""
    limiter = RateLimiter(db_session)
    
    # Verify no record exists
    record = db_session.query(RateLimit).filter(
        RateLimit.user_id == 1,
        RateLimit.endpoint == "new_endpoint"
    ).first()
    assert record is None
    
    # Increment should create record
    count = limiter.increment(user_id=1, endpoint="new_endpoint")
    assert count == 1
    
    # Verify record was created
    record = db_session.query(RateLimit).filter(
        RateLimit.user_id == 1,
        RateLimit.endpoint == "new_endpoint"
    ).first()
    assert record is not None
    assert record.current_count == 1


def test_increment_resets_expired_window(db_session):
    """Test that increment resets expired window."""
    limiter = RateLimiter(db_session)
    
    # Create expired rate limit
    expired = RateLimit(
        user_id=1,
        endpoint="test",
        limit_count=10,
        window_seconds=1,
        current_count=5,
        window_start=datetime.now() - timedelta(seconds=2)
    )
    db_session.add(expired)
    db_session.commit()
    
    # Increment should reset window
    count = limiter.increment(user_id=1, endpoint="test")
    assert count == 1  # Reset to 1


def test_reset_window(db_session):
    """Test manually resetting rate limit window."""
    limiter = RateLimiter(db_session)
    
    # Create rate limit at limit
    limiter.increment(user_id=1, endpoint="test")
    for i in range(RATE_LIMITS["default"]["limit"] - 1):
        limiter.increment(user_id=1, endpoint="test")
    
    # Should be at limit
    allowed, _ = limiter.check_limit(user_id=1, endpoint="test")
    assert allowed is False
    
    # Reset window
    result = limiter.reset_window(user_id=1, endpoint="test")
    assert result is True
    
    # Should be allowed again
    allowed, remaining = limiter.check_limit(user_id=1, endpoint="test")
    assert allowed is True
    assert remaining > 0


def test_reset_window_nonexistent(db_session):
    """Test resetting non-existent rate limit."""
    limiter = RateLimiter(db_session)
    
    result = limiter.reset_window(user_id=1, endpoint="nonexistent")
    
    assert result is False


def test_get_limits(db_session):
    """Test getting all rate limits for a user."""
    limiter = RateLimiter(db_session)
    
    # Create limits for multiple endpoints
    limiter.increment(user_id=1, endpoint="endpoint1")
    limiter.increment(user_id=1, endpoint="endpoint2")
    limiter.increment(user_id=1, endpoint="endpoint2")
    
    limits = limiter.get_limits(user_id=1)
    
    assert "endpoint1" in limits
    assert "endpoint2" in limits
    assert limits["endpoint1"]["current"] == 1
    assert limits["endpoint2"]["current"] == 2


def test_get_limits_includes_metadata(db_session):
    """Test that get_limits includes all metadata."""
    limiter = RateLimiter(db_session)
    
    limiter.increment(user_id=1, endpoint="test")
    
    limits = limiter.get_limits(user_id=1)
    
    assert "test" in limits
    limit_info = limits["test"]
    
    assert "limit" in limit_info
    assert "current" in limit_info
    assert "remaining" in limit_info
    assert "reset_in_seconds" in limit_info
    assert "window_seconds" in limit_info
    assert "window_start" in limit_info


def test_get_time_until_reset(db_session):
    """Test getting time until reset."""
    limiter = RateLimiter(db_session)
    
    # Create rate limit
    limiter.increment(user_id=1, endpoint="test")
    
    # Get time until reset
    time_until_reset = limiter.get_time_until_reset(user_id=1, endpoint="test")
    
    # Should be close to window_seconds
    window_seconds = RATE_LIMITS["default"]["window_seconds"]
    assert 0 <= time_until_reset <= window_seconds


def test_get_time_until_reset_nonexistent(db_session):
    """Test getting time until reset for non-existent limit."""
    limiter = RateLimiter(db_session)
    
    time_until_reset = limiter.get_time_until_reset(user_id=1, endpoint="nonexistent")
    
    assert time_until_reset == 0


def test_cleanup_expired_windows(db_session):
    """Test cleaning up expired rate limit records."""
    limiter = RateLimiter(db_session)
    
    # Create old rate limit records
    old_record1 = RateLimit(
        user_id=1,
        endpoint="old1",
        limit_count=10,
        window_seconds=60,
        current_count=5,
        window_start=datetime.now() - timedelta(hours=25)
    )
    old_record2 = RateLimit(
        user_id=1,
        endpoint="old2",
        limit_count=10,
        window_seconds=60,
        current_count=5,
        window_start=datetime.now() - timedelta(hours=26)
    )
    # Create recent record
    recent_record = RateLimit(
        user_id=1,
        endpoint="recent",
        limit_count=10,
        window_seconds=60,
        current_count=5,
        window_start=datetime.now() - timedelta(hours=1)
    )
    
    db_session.add_all([old_record1, old_record2, recent_record])
    db_session.commit()
    
    # Cleanup records older than 24 hours
    deleted_count = limiter.cleanup_expired_windows(hours=24)
    
    assert deleted_count == 2
    
    # Verify recent record still exists
    remaining = db_session.query(RateLimit).filter(
        RateLimit.endpoint == "recent"
    ).first()
    assert remaining is not None


def test_endpoint_specific_limits(db_session):
    """Test that different endpoints have different configured limits."""
    limiter = RateLimiter(db_session)
    
    # Test chat endpoint (lower limit)
    for i in range(RATE_LIMITS["chat"]["limit"]):
        limiter.increment(user_id=1, endpoint="chat")
    
    allowed, remaining = limiter.check_limit(user_id=1, endpoint="chat")
    assert allowed is False
    
    # Test export endpoint (even lower limit)
    for i in range(RATE_LIMITS["export"]["limit"]):
        limiter.increment(user_id=2, endpoint="export")
    
    allowed, remaining = limiter.check_limit(user_id=2, endpoint="export")
    assert allowed is False


def test_check_limit_before_increment(db_session):
    """Test checking limit before incrementing."""
    limiter = RateLimiter(db_session)
    
    # Check limit (should create record but not increment)
    allowed1, remaining1 = limiter.check_limit(user_id=1, endpoint="test")
    assert allowed1 is True
    
    # Increment
    count = limiter.increment(user_id=1, endpoint="test")
    assert count == 1
    
    # Check again
    allowed2, remaining2 = limiter.check_limit(user_id=1, endpoint="test")
    assert allowed2 is True
    assert remaining2 == remaining1 - 1
