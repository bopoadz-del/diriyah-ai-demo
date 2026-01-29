"""Worker to project Redis Stream events into the database."""

from __future__ import annotations

import logging
import os
import socket
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal
from backend.events.envelope import EventEnvelope
from backend.events.projector import EventProjector

logger = logging.getLogger(__name__)

STREAM_NAME = "events:global"
CONSUMER_GROUP = "events"
CLAIM_IDLE_MS = 60000


def _consumer_name() -> str:
    return os.getenv("HOSTNAME") or f"event-projector-{socket.gethostname()}-{os.getpid()}"


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_event(fields: Dict[str, Any]) -> EventEnvelope:
    return EventEnvelope(
        event_id=str(fields.get("event_id", "")),
        event_type=str(fields.get("event_type", "")),
        ts=str(fields.get("ts", "")),
        workspace_id=_safe_int(fields.get("workspace_id")),
        actor_id=_safe_int(fields.get("actor_id")),
        correlation_id=fields.get("correlation_id") or None,
        source=str(fields.get("source") or "unknown"),
        payload_json=str(fields.get("payload_json") or "{}"),
    )


def _decode_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    decoded: Dict[str, Any] = {}
    for key, value in fields.items():
        decoded[str(key)] = value
    return decoded


def _parse_stream_response(response: List[Tuple[str, List[Tuple[str, Dict[str, Any]]]]]) -> List[Tuple[str, Dict[str, Any]]]:
    entries: List[Tuple[str, Dict[str, Any]]] = []
    for _, messages in response:
        for entry_id, fields in messages:
            entries.append((entry_id, _decode_fields(fields)))
    return entries


def _connect_redis() -> Optional[object]:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("REDIS_URL not configured for event projector worker")
        return None
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        if hasattr(client, "ping"):
            client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis unavailable for event projector worker: %s", exc)
        return None


def _ensure_group(redis_client: object) -> None:
    try:
        redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="$", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" in str(exc):
            return
        raise


def _claim_pending(redis_client: object, consumer: str) -> List[Tuple[str, Dict[str, Any]]]:
    if hasattr(redis_client, "xautoclaim"):
        _, messages = redis_client.xautoclaim(
            STREAM_NAME,
            CONSUMER_GROUP,
            consumer,
            CLAIM_IDLE_MS,
            start_id="0-0",
            count=10,
        )
        return [(entry_id, _decode_fields(fields)) for entry_id, fields in messages]

    pending = redis_client.xpending_range(
        STREAM_NAME,
        CONSUMER_GROUP,
        min="-",
        max="+",
        count=10,
    )
    entry_ids = [item["message_id"] for item in pending]
    if not entry_ids:
        return []
    claimed = redis_client.xclaim(
        STREAM_NAME,
        CONSUMER_GROUP,
        consumer,
        min_idle_time=CLAIM_IDLE_MS,
        message_ids=entry_ids,
    )
    return [(entry_id, _decode_fields(fields)) for entry_id, fields in claimed]


def _read_new(redis_client: object, consumer: str) -> List[Tuple[str, Dict[str, Any]]]:
    response = redis_client.xreadgroup(
        CONSUMER_GROUP,
        consumer,
        streams={STREAM_NAME: ">"},
        count=10,
        block=2000,
    )
    return _parse_stream_response(response)


def _process_entry(entry_id: str, fields: Dict[str, Any], db: Session, redis_client: object) -> None:
    event = _parse_event(fields)
    EventProjector.apply(event, db)
    redis_client.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)


def run_forever() -> None:
    consumer = _consumer_name()
    logger.info("Event projector worker starting", extra={"consumer": consumer})

    while True:
        redis_client = _connect_redis()
        if redis_client is None:
            time.sleep(2)
            continue

        try:
            _ensure_group(redis_client)
            pending = _claim_pending(redis_client, consumer)
            entries = pending + _read_new(redis_client, consumer)
            if not entries:
                continue
            for entry_id, fields in entries:
                db = SessionLocal()
                try:
                    _process_entry(entry_id, fields, db, redis_client)
                except Exception as exc:
                    logger.exception("Failed to project event %s: %s", entry_id, exc)
                finally:
                    db.close()
        except Exception as exc:
            logger.warning("Event projector loop error: %s", exc)
            time.sleep(1)


if __name__ == "__main__":
    run_forever()
