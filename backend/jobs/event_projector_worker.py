"""Worker to project events from Redis Streams."""

from __future__ import annotations

import logging
import os
import socket
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal
from backend.events.emitter import GLOBAL_STREAM, GROUP_NAME
from backend.events.envelope import EventEnvelope
from backend.events.models import EventOffset
from backend.events.projector import EventProjector

logger = logging.getLogger(__name__)


def _consumer_name() -> str:
    return os.getenv("HOSTNAME") or f"events-{socket.gethostname()}-{os.getpid()}"


def _decode_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    decoded: Dict[str, Any] = {}
    for key, value in fields.items():
        if isinstance(value, bytes):
            decoded[key] = value.decode()
        else:
            decoded[key] = value
    return decoded


class EventProjectorWorker:
    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis = None

    def _connect(self) -> object:
        if self._redis is not None:
            return self._redis
        if not self._redis_url:
            raise RuntimeError("REDIS_URL is not configured for event projection")
        import redis  # type: ignore

        self._redis = redis.Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    def ensure_group(self, stream: str = GLOBAL_STREAM, group: str = GROUP_NAME) -> None:
        redis_client = self._connect()
        try:
            redis_client.xgroup_create(stream, group, id="$", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" in str(exc):
                return
            raise

    def read(self, stream: str, group: str, consumer: str, count: int = 10, block_ms: int = 2000) -> List[Tuple[str, Dict[str, Any]]]:
        redis_client = self._connect()
        response = redis_client.xreadgroup(
            group,
            consumer,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )
        entries: List[Tuple[str, Dict[str, Any]]] = []
        for _stream, stream_entries in response or []:
            for entry_id, fields in stream_entries:
                entries.append((entry_id, _decode_fields(fields)))
        return entries

    def claim(self, stream: str, group: str, consumer: str, min_idle_ms: int = 60000) -> List[Tuple[str, Dict[str, Any]]]:
        redis_client = self._connect()
        if hasattr(redis_client, "xautoclaim"):
            _, messages = redis_client.xautoclaim(stream, group, consumer, min_idle_ms, start_id="0-0", count=10)
            return [(entry_id, _decode_fields(fields)) for entry_id, fields in messages]

        pending = redis_client.xpending_range(stream, group, min="-", max="+", count=10)
        entry_ids = [item["message_id"] for item in pending]
        if not entry_ids:
            return []
        claimed = redis_client.xclaim(stream, group, consumer, min_idle_ms, entry_ids)
        return [(entry_id, _decode_fields(fields)) for entry_id, fields in claimed]

    def ack(self, stream: str, group: str, entry_id: str) -> None:
        redis_client = self._connect()
        redis_client.xack(stream, group, entry_id)

    def run_once(self) -> int:
        consumer = _consumer_name()
        self.ensure_group()
        claimed = self.claim(GLOBAL_STREAM, GROUP_NAME, consumer)
        entries = claimed + self.read(GLOBAL_STREAM, GROUP_NAME, consumer, count=10, block_ms=100)

        processed = 0
        for entry_id, fields in entries:
            db = SessionLocal()
            try:
                envelope = EventEnvelope.from_fields(fields)
                projector = EventProjector()
                projector.apply(envelope, db, stream=GLOBAL_STREAM, stream_entry_id=entry_id)
                self._update_offset(db, GLOBAL_STREAM, GROUP_NAME, entry_id)
                db.commit()
                self.ack(GLOBAL_STREAM, GROUP_NAME, entry_id)
                processed += 1
            finally:
                db.close()
        return processed

    def _update_offset(self, db: Session, stream: str, group: str, entry_id: str) -> None:
        offset = db.query(EventOffset).filter_by(stream=stream).one_or_none()
        if not offset:
            offset = EventOffset(stream=stream, group_name=group, last_entry_id=entry_id)
            db.add(offset)
        else:
            offset.last_entry_id = entry_id


def run_forever() -> None:
    worker = EventProjectorWorker()
    consumer = _consumer_name()
    worker.ensure_group()
    logger.info("Event projector worker starting", extra={"consumer": consumer})

    while True:
        try:
            processed = worker.run_once()
            if processed == 0:
                time.sleep(1)
        except Exception as exc:
            logger.exception("Event projector worker error: %s", exc)
            time.sleep(1)


if __name__ == "__main__":
    run_forever()
