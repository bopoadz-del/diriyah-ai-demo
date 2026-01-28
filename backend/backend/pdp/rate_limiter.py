"""Rate limiting implementation using sliding window counter algorithm."""

from typing import Dict, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import RateLimit


# Default rate limits per endpoint (requests per window)
RATE_LIMITS = {
    "default": {"limit": 100, "window_seconds": 60},
    "chat": {"limit": 50, "window_seconds": 60},
    "search": {"limit": 30, "window_seconds": 60},
    "export": {"limit": 10, "window_seconds": 60},
    "upload": {"limit": 20, "window_seconds": 60},
    "ai": {"limit": 50, "window_seconds": 60},
    "api": {"limit": 100, "window_seconds": 60},
}


class RateLimiter:
    """
    Rate limiter using sliding window counter algorithm.
    
    Tracks request counts per user and endpoint within time windows.
    """
    
    def __init__(self, db: Session):
        """
        Initialize RateLimiter.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def check_limit(self, user_id: int, endpoint: str) -> Tuple[bool, int]:
        """
        Check if user is within rate limit for endpoint.
        
        Args:
            user_id: User ID
            endpoint: Endpoint identifier
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        # Get rate limit configuration
        config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
        limit = config["limit"]
        window_seconds = config["window_seconds"]
        
        # Get or create rate limit record
        rate_limit = self.db.query(RateLimit).filter(
            RateLimit.user_id == user_id,
            RateLimit.endpoint == endpoint
        ).first()
        
        if not rate_limit:
            # First request - create record
            rate_limit = RateLimit(
                user_id=user_id,
                endpoint=endpoint,
                limit_count=limit,
                window_seconds=window_seconds,
                current_count=0,
                window_start=datetime.now()
            )
            self.db.add(rate_limit)
            self.db.commit()
            return True, limit
        
        # Check if window has expired
        window_age = (datetime.now() - rate_limit.window_start).total_seconds()
        
        if window_age >= rate_limit.window_seconds:
            # Window expired - reset
            rate_limit.window_start = datetime.now()
            rate_limit.current_count = 0
            rate_limit.limit_count = limit
            rate_limit.window_seconds = window_seconds
            self.db.commit()
            return True, limit
        
        # Check if limit exceeded
        if rate_limit.current_count >= rate_limit.limit_count:
            return False, 0
        
        # Within limit
        remaining = rate_limit.limit_count - rate_limit.current_count
        return True, remaining
    
    def increment(self, user_id: int, endpoint: str) -> int:
        """
        Increment request counter for user and endpoint.
        
        Args:
            user_id: User ID
            endpoint: Endpoint identifier
            
        Returns:
            Current count after increment
        """
        rate_limit = self.db.query(RateLimit).filter(
            RateLimit.user_id == user_id,
            RateLimit.endpoint == endpoint
        ).first()
        
        if not rate_limit:
            # Create new record
            config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
            rate_limit = RateLimit(
                user_id=user_id,
                endpoint=endpoint,
                limit_count=config["limit"],
                window_seconds=config["window_seconds"],
                current_count=1,
                window_start=datetime.now()
            )
            self.db.add(rate_limit)
            self.db.commit()
            return 1
        
        # Check if window expired
        window_age = (datetime.now() - rate_limit.window_start).total_seconds()
        
        if window_age >= rate_limit.window_seconds:
            # Reset window
            rate_limit.window_start = datetime.now()
            rate_limit.current_count = 1
        else:
            # Increment counter
            rate_limit.current_count += 1
        
        self.db.commit()
        return rate_limit.current_count
    
    def reset_window(self, user_id: int, endpoint: str) -> bool:
        """
        Manually reset rate limit window for user and endpoint.
        
        Args:
            user_id: User ID
            endpoint: Endpoint identifier
            
        Returns:
            True if reset successful, False if record not found
        """
        rate_limit = self.db.query(RateLimit).filter(
            RateLimit.user_id == user_id,
            RateLimit.endpoint == endpoint
        ).first()
        
        if not rate_limit:
            return False
        
        rate_limit.window_start = datetime.now()
        rate_limit.current_count = 0
        self.db.commit()
        return True
    
    def get_limits(self, user_id: int) -> Dict[str, Dict]:
        """
        Get current rate limit status for all endpoints for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict mapping endpoint to limit status info
        """
        rate_limits = self.db.query(RateLimit).filter(
            RateLimit.user_id == user_id
        ).all()
        
        result = {}
        
        for rate_limit in rate_limits:
            # Calculate remaining time in window
            window_age = (datetime.now() - rate_limit.window_start).total_seconds()
            remaining_time = max(0, rate_limit.window_seconds - window_age)
            
            # Calculate remaining requests
            remaining_requests = max(0, rate_limit.limit_count - rate_limit.current_count)
            
            # Check if window expired
            if window_age >= rate_limit.window_seconds:
                # Window expired - show reset values
                remaining_requests = rate_limit.limit_count
                remaining_time = rate_limit.window_seconds
            
            result[rate_limit.endpoint] = {
                "limit": rate_limit.limit_count,
                "current": rate_limit.current_count,
                "remaining": remaining_requests,
                "reset_in_seconds": int(remaining_time),
                "window_seconds": rate_limit.window_seconds,
                "window_start": rate_limit.window_start.isoformat()
            }
        
        return result
    
    def get_time_until_reset(self, user_id: int, endpoint: str) -> int:
        """
        Get seconds until rate limit window resets.
        
        Args:
            user_id: User ID
            endpoint: Endpoint identifier
            
        Returns:
            Seconds until reset, or 0 if no limit exists
        """
        rate_limit = self.db.query(RateLimit).filter(
            RateLimit.user_id == user_id,
            RateLimit.endpoint == endpoint
        ).first()
        
        if not rate_limit:
            return 0
        
        window_age = (datetime.now() - rate_limit.window_start).total_seconds()
        remaining_time = max(0, rate_limit.window_seconds - window_age)
        
        return int(remaining_time)
    
    def cleanup_expired_windows(self, hours: int = 24) -> int:
        """
        Clean up rate limit records with expired windows.
        
        Args:
            hours: Remove records older than this many hours
            
        Returns:
            Number of records deleted
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        deleted_count = self.db.query(RateLimit).filter(
            RateLimit.window_start < cutoff_time
        ).delete()
        
        self.db.commit()
        return deleted_count
