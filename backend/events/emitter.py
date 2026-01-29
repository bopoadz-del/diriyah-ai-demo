"""Redis Streams event emitter."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from backend.events.envelope import EventEnvelope
from backend.events.projector import EventProjector

logger = logging.getLogger(__name__)

GLOBAL_STREAM = "events:global"
WORKSPACE_STREAM_PREFIX = "events:workspace:"
GROUP_NAME = "events"


class EventEmitter:
    def __init__(
        self,
        *,
        db: Optional[Session] = None,
        redis_url: Optional[str] = None,
        degraded: bool = True,
    ) -> None:
        self._db = db
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._degraded = degraded
        self._redis = None
        self._warned = False

    def _connect(self) -> Optional[object]:
        if self._redis is not None:
            return self._redis
        if not self._redis_url:
            if not self._warned:
                logger.warning("REDIS_URL not set; using degraded event emission")
                self._warned = True
            return None
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(self._redis_url, decode_responses=True)
            if hasattr(client, "ping"):
                client.ping()
            self._redis = client
            return client
        except Exception as exc:
            if not self._warned:
                logger.warning("Redis event stream unavailable: %s", exc)
                self._warned = True
            return None

    def emit_global(self, event: EventEnvelope) -> Optional[str]:
        return self._emit(GLOBAL_STREAM, event)

    def emit_workspace(self, workspace_id: int, event: EventEnvelope) -> Optional[str]:
        return self._emit(f"{WORKSPACE_STREAM_PREFIX}{workspace_id}", event)

    def emit(self, event: EventEnvelope) -> Optional[str]:
        stream_id = self.emit_global(event)
        if event.workspace_id is not None:
            self.emit_workspace(event.workspace_id, event)
        return stream_id

    def _emit(self, stream: str, event: EventEnvelope) -> Optional[str]:
        redis_client = self._connect()
        if redis_client is None:
            if not self._degraded:
                raise RuntimeError("Redis is unavailable for event emission")
            return self._record_degraded(stream, event)
        return redis_client.xadd(stream, event.to_fields())

    def _record_degraded(self, stream: str, event: EventEnvelope) -> Optional[str]:
        if self._db is None:
            logger.warning("Skipping event emission; no DB session for degraded mode")
            return None
        projector = EventProjector()
        projector.apply(event, self._db, stream=stream, stream_entry_id=None)
        return None


def emit_global(event: EventEnvelope, *, db: Optional[Session] = None) -> Optional[str]:
    return EventEmitter(db=db).emit_global(event)


def emit_workspace(workspace_id: int, event: EventEnvelope, *, db: Optional[Session] = None) -> Optional[str]:
    return EventEmitter(db=db).emit_workspace(workspace_id, event)
