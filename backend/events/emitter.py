"""Redis Streams-backed event emitter with DB fallback."""

from __future__ import annotations

from dataclasses import replace
import logging
import os
from typing import Callable, Iterable, Optional

from backend.backend.db import SessionLocal
from backend.events.envelope import EventEnvelope
from backend.events.models import EventLog

logger = logging.getLogger(__name__)

GLOBAL_STREAM = "events:global"
WORKSPACE_STREAM_TEMPLATE = "events:workspace:{workspace_id}"


class EventEmitter:
    """Simple in-process emitter retained for legacy regression hooks."""

    def __init__(self, handlers: Optional[Iterable[Callable[[EventEnvelope], None]]] = None) -> None:
        self._handlers = list(handlers or [])

    def emit(self, event: EventEnvelope) -> None:
        for handler in self._handlers:
            handler(event)

    def register(self, handler: Callable[[EventEnvelope], None]) -> None:
        self._handlers.append(handler)


def _get_redis_client() -> Optional[object]:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        if hasattr(client, "ping"):
            client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis unavailable for event emitter: %s", exc)
        return None


def _write_event_log(event: EventEnvelope) -> None:
    session = SessionLocal()
    try:
        session.add(
            EventLog(
                event_id=event.event_id,
                event_type=event.event_type,
                ts=event.ts,
                workspace_id=event.workspace_id,
                actor_id=event.actor_id,
                correlation_id=event.correlation_id,
                source=event.source,
                payload_json=event.payload_json,
            )
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.warning("Failed to write event_log fallback: %s", exc)
    finally:
        session.close()


def emit_global(event: EventEnvelope) -> Optional[str]:
    redis_client = _get_redis_client()
    if redis_client is None:
        logger.warning("Redis not configured; falling back to event_log for %s", event.event_type)
        _write_event_log(event)
        return None

    fields = event.to_fields()
    try:
        stream_id = redis_client.xadd(GLOBAL_STREAM, fields)
        if event.workspace_id is not None:
            workspace_stream = WORKSPACE_STREAM_TEMPLATE.format(workspace_id=event.workspace_id)
            redis_client.xadd(workspace_stream, fields)
        return stream_id
    except Exception as exc:
        logger.warning("Failed to emit event to Redis: %s", exc)
        _write_event_log(event)
        return None


def emit_workspace(workspace_id: int, event: EventEnvelope) -> Optional[str]:
    if event.workspace_id != workspace_id:
        event = replace(event, workspace_id=workspace_id)
    return emit_global(event)
