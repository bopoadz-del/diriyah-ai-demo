"""Distributed lock helpers for hydration worker."""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional

from sqlalchemy.orm import Session

from backend.hydration.models import HydrationLock

logger = logging.getLogger(__name__)


class LockManager:
    def __init__(self, db: Session, ttl_seconds: int = 600) -> None:
        self.db = db
        self.ttl = timedelta(seconds=ttl_seconds)
        self.owner = f"hydration-{uuid.uuid4()}"
        self.redis_url = os.getenv("REDIS_URL")
        self._redis = None
        if self.redis_url:
            import redis  # type: ignore
            self._redis = redis.Redis.from_url(self.redis_url)

    @contextmanager
    def acquire(self, workspace_id: str) -> Iterator[bool]:
        if self._redis:
            token = self._acquire_redis(workspace_id)
            try:
                yield token is not None
            finally:
                if token:
                    self._release_redis(workspace_id, token)
            return

        acquired = self._acquire_db(workspace_id)
        try:
            yield acquired
        finally:
            if acquired:
                self._release_db(workspace_id)

    def _acquire_redis(self, workspace_id: str) -> Optional[str]:
        token = str(uuid.uuid4())
        key = f"hydration:lock:{workspace_id}"
        if self._redis.set(key, token, nx=True, ex=int(self.ttl.total_seconds())):
            return token
        return None

    def _release_redis(self, workspace_id: str, token: str) -> None:
        key = f"hydration:lock:{workspace_id}"
        value = self._redis.get(key)
        if value and value.decode() == token:
            self._redis.delete(key)

    def _acquire_db(self, workspace_id: str) -> bool:
        now = datetime.now(timezone.utc)
        expires = now + self.ttl
        lock = self.db.query(HydrationLock).filter(HydrationLock.workspace_id == workspace_id).one_or_none()
        if lock:
            if lock.locked_until > now:
                return False
            lock.locked_until = expires
            lock.owner = self.owner
        else:
            lock = HydrationLock(workspace_id=workspace_id, locked_until=expires, owner=self.owner)
            self.db.add(lock)
        self.db.commit()
        return True

    def _release_db(self, workspace_id: str) -> None:
        lock = self.db.query(HydrationLock).filter(HydrationLock.workspace_id == workspace_id).one_or_none()
        if lock and lock.owner == self.owner:
            lock.locked_until = datetime.now(timezone.utc)
            self.db.commit()
