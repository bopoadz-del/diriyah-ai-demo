"""Worker to project Redis Streams events into DB state."""

from __future__ import annotations

import logging
import os
import socket
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal
from backend.events.envelope import EventEnvelope
from backend.events.emitter import CONSUMER_GROUP, GLOBAL_STREAM
from backend.events.projector import EventProjector

logger = logging.getLogger(__name__)


def _consumer_name() -> str:
    return os.getenv("HOSTNAME") or f"events-{socket.gethostname()}-{os.getpid()}"


def _connect_redis() -> object:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is not configured for event projector")
    import redis  # type: ignore

    client = redis.Redis.from_url(redis_url, decode_responses=True)
    if hasattr(client, "ping"):
        client.ping()
    return client


def _ensure_group(redis_client: object, stream: str, group: str) -> None:
    try:
        redis_client.xgroup_create(stream, group, id="$", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" in str(exc):
            return
        raise


def _decode_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    decoded: Dict[str, Any] = {}
    for key, value in fields.items():
        decoded[key] = value.decode() if isinstance(value, bytes) else value
    return decoded


def _parse_response(response: Iterable) -> List[Tuple[str, Dict[str, Any]]]:
    entries: List[Tuple[str, Dict[str, Any]]] = []
    for _stream_name, stream_entries in response or []:
        for entry_id, fields in stream_entries:
            entries.append((entry_id, _decode_fields(fields)))
    return entries


def _claim_pending(redis_client: object, consumer: str, min_idle_ms: int = 60000) -> List[Tuple[str, Dict[str, Any]]]:
    if hasattr(redis_client, "xautoclaim"):
        _, messages = redis_client.xautoclaim(
            GLOBAL_STREAM,
            CONSUMER_GROUP,
            consumer,
            min_idle_ms,
            start_id="0-0",
            count=10,
        )
        return [(entry_id, _decode_fields(fields)) for entry_id, fields in messages]

    pending = redis_client.xpending_range(GLOBAL_STREAM, CONSUMER_GROUP, min="-", max="+", count=10)
    entry_ids = [item["message_id"] for item in pending]
    if not entry_ids:
        return []
    claimed = redis_client.xclaim(
        GLOBAL_STREAM,
        CONSUMER_GROUP,
        consumer,
        min_idle_ms,
        entry_ids,
    )
    return [(entry_id, _decode_fields(fields)) for entry_id, fields in claimed]


def process_once(db_factory=SessionLocal) -> int:
    redis_client = _connect_redis()
    consumer = _consumer_name()
    _ensure_group(redis_client, GLOBAL_STREAM, CONSUMER_GROUP)

    claimed = _claim_pending(redis_client, consumer)
    response = redis_client.xreadgroup(
        CONSUMER_GROUP,
        consumer,
        streams={GLOBAL_STREAM: ">"},
        count=10,
        block=100,
    )
    entries = claimed + _parse_response(response)

    processed = 0
    projector = EventProjector()
    for entry_id, fields in entries:
        db: Session = db_factory()
        try:
            event = EventEnvelope.from_fields(fields)
            applied = projector.apply(event, db, stream=GLOBAL_STREAM, stream_entry_id=entry_id)
            if applied:
                logger.info("Projected event", extra={"event_id": event.event_id})
            redis_client.xack(GLOBAL_STREAM, CONSUMER_GROUP, entry_id)
            processed += 1
        except Exception as exc:
            logger.exception("Failed to project event %s: %s", entry_id, exc)
            db.rollback()
        finally:
            db.close()
    return processed


def run_forever() -> None:
    while True:
        try:
            processed = process_once()
            if processed == 0:
                time.sleep(0.5)
        except Exception as exc:
            logger.exception("Event projector loop error: %s", exc)
            time.sleep(1)


if __name__ == "__main__":
    run_forever()
