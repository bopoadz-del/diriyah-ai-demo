"""Redis-backed distributed lock helpers."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""

_EXTEND_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
end
return 0
"""


class DistributedLock:
    """Simple Redis-backed distributed lock.

    If Redis is not configured or unavailable, the lock becomes a no-op and
    allows execution to continue while logging a warning.
    """

    _NO_LOCK_TOKEN = "__NO_REDIS_LOCK__"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_client: Optional[object] = None,
    ) -> None:
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis = redis_client
        self._warned = False

        if self._redis is None and self._redis_url:
            try:
                import redis  # type: ignore

                self._redis = redis.Redis.from_url(self._redis_url)
            except Exception as exc:  # pragma: no cover - defensive guard
                self._redis = None
                self._log_degraded(f"Redis client init failed: {exc}")

    def acquire(self, key: str, ttl: int, wait_seconds: float = 0) -> Optional[str]:
        """Attempt to acquire a lock.

        Returns a token string if acquired, None if another owner holds the lock.
        If Redis is not available, returns a sentinel token to indicate no lock.
        """

        if self._redis is None:
            self._log_degraded("REDIS_URL not set")
            return self._NO_LOCK_TOKEN

        token = str(uuid.uuid4())
        deadline = time.monotonic() + max(wait_seconds, 0)
        ttl_seconds = max(int(ttl), 1)

        while True:
            try:
                acquired = self._redis.set(key, token, nx=True, ex=ttl_seconds)
            except Exception as exc:  # pragma: no cover - network failure fallback
                self._log_degraded(f"Redis unavailable: {exc}")
                return self._NO_LOCK_TOKEN

            if acquired:
                return token
            if wait_seconds <= 0 or time.monotonic() >= deadline:
                return None
            time.sleep(0.1)

    def release(self, key: str, token: Optional[str]) -> bool:
        """Release a lock if the token matches."""

        if token is None:
            return False
        if self._redis is None or token == self._NO_LOCK_TOKEN:
            return True
        try:
            result = self._redis.eval(_RELEASE_SCRIPT, 1, key, token)
            return bool(result)
        except Exception as exc:  # pragma: no cover - network failure fallback
            logger.warning("Failed to release Redis lock %s: %s", key, exc)
            return False

    def extend(self, key: str, token: Optional[str], ttl: int) -> bool:
        """Extend a lock TTL if the token matches."""

        if token is None:
            return False
        if self._redis is None or token == self._NO_LOCK_TOKEN:
            return True
        ttl_seconds = max(int(ttl), 1)
        try:
            result = self._redis.eval(_EXTEND_SCRIPT, 1, key, token, ttl_seconds)
            return bool(result)
        except Exception as exc:  # pragma: no cover - network failure fallback
            logger.warning("Failed to extend Redis lock %s: %s", key, exc)
            return False

    def _log_degraded(self, reason: str) -> None:
        if self._warned:
            return
        logger.warning("Redis locks disabled (%s); proceeding without distributed lock.", reason)
        self._warned = True
