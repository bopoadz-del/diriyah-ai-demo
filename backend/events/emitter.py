"""Redis Streams event emitter."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.events.envelope import EventEnvelope
from backend.events.models import EventLog

logger = logging.getLogger(__name__)

GLOBAL_STREAM = "events:global"
WORKSPACE_STREAM_PREFIX = "events:workspace:"
CONSUMER_GROUP = "events"


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass
class EmitResult:
    stream: str
    entry_id: Optional[str]


class EventEmitter:
    def __init__(
        self,
        redis_client: Optional[object] = None,
        redis_url: Optional[str] = None,
        strict: Optional[bool] = None,
    ) -> None:
        self._redis = redis_client
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._strict = strict if strict is not None else _env_flag("EVENTS_STRICT", False)
        self._warned = False

    def connect(self) -> Optional[object]:
        if self._redis is not None:
            return self._redis
        if not self._redis_url:
            return self._handle_degraded("REDIS_URL not configured")
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(self._redis_url, decode_responses=True)
            if hasattr(client, "ping"):
                client.ping()
            self._redis = client
            return client
        except Exception as exc:
            return self._handle_degraded(f"Redis unavailable: {exc}")

    def emit_global(self, event: EventEnvelope, db: Optional[Session] = None) -> EmitResult:
        return self._emit(GLOBAL_STREAM, event, db)

    def emit_workspace(self, workspace_id: int, event: EventEnvelope, db: Optional[Session] = None) -> EmitResult:
        return self._emit(f"{WORKSPACE_STREAM_PREFIX}{workspace_id}", event, db)

    def _emit(self, stream: str, event: EventEnvelope, db: Optional[Session]) -> EmitResult:
        client = self.connect()
        if client is None:
            if db is not None:
                self._record_event(db, event, stream)
            return EmitResult(stream=stream, entry_id=None)

        entry_id = client.xadd(stream, event.to_fields())
        return EmitResult(stream=stream, entry_id=entry_id)

    def _record_event(self, db: Session, event: EventEnvelope, stream: str) -> None:
        try:
            payload = json.loads(event.payload_json)
        except json.JSONDecodeError:
            payload = {"raw": event.payload_json}
        db.add(
            EventLog(
                event_id=event.event_id,
                stream=stream,
                stream_entry_id=None,
                event_type=event.event_type,
                workspace_id=event.workspace_id,
                actor_id=event.actor_id,
                correlation_id=event.correlation_id,
                payload_json=payload,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()

    def _handle_degraded(self, reason: str) -> Optional[object]:
        if self._strict:
            raise RuntimeError(reason)
        if not self._warned:
            logger.warning("Event emitter degraded: %s", reason)
            self._warned = True
        return None
