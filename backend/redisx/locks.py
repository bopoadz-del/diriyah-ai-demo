"""Redis-backed distributed locks."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Optional

import redis

logger = logging.getLogger(__name__)

_RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
else
  return 0
end
"""

_EXTEND_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("expire", KEYS[1], ARGV[2])
else
  return 0
end
"""


class DistributedLock:
    def __init__(self, redis_url: Optional[str] = None, lock_logger: Optional[logging.Logger] = None) -> None:
        self._logger = lock_logger or logger
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis: Optional[redis.Redis] = None
        self._degraded = False

        if self._redis_url:
            self._redis = redis.Redis.from_url(self._redis_url, decode_responses=True)
        else:
            self._degraded = True
            self._logger.warning("REDIS_URL not set; distributed locks disabled.")

    def acquire(self, key: str, ttl: int, wait_seconds: int = 0) -> Optional[str]:
        if self._redis is None:
            return self._noop_token()

        token = uuid.uuid4().hex
        deadline = time.monotonic() + max(wait_seconds, 0)
        ttl_seconds = max(int(ttl), 1)

        while True:
            try:
                if self._redis.set(key, token, nx=True, ex=ttl_seconds):
                    return token
            except redis.exceptions.RedisError as exc:
                self._degrade(key, exc)
                return self._noop_token()

            if time.monotonic() >= deadline:
                return None
            time.sleep(min(0.2, max(deadline - time.monotonic(), 0)))

    def release(self, key: str, token: str) -> bool:
        if self._redis is None or token.startswith("noop-"):
            return True

        try:
            result = self._redis.eval(_RELEASE_LUA, 1, key, token)
        except redis.exceptions.RedisError as exc:
            self._degrade(key, exc)
            return False
        return bool(result)

    def extend(self, key: str, token: str, ttl: int) -> bool:
        if self._redis is None or token.startswith("noop-"):
            return False

        ttl_seconds = max(int(ttl), 1)
        try:
            result = self._redis.eval(_EXTEND_LUA, 1, key, token, ttl_seconds)
        except redis.exceptions.RedisError as exc:
            self._degrade(key, exc)
            return False
        return bool(result)

    def _noop_token(self) -> str:
        return f"noop-{uuid.uuid4().hex}"

    def _degrade(self, key: str, exc: Exception) -> None:
        if self._degraded:
            return
        self._degraded = True
        self._redis = None
        self._logger.warning("Redis lock degraded for %s: %s", key, exc)
