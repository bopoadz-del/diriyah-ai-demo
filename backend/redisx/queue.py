"""Redis Streams-backed job queue helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal
from backend.ops.models import BackgroundJob, BackgroundJobEvent

logger = logging.getLogger(__name__)


STREAM_NAME = "jobs:main"
DLQ_STREAM_NAME = "jobs:dlq"
CONSUMER_GROUP = "jobs"


@dataclass(frozen=True)
class QueueEntry:
    entry_id: str
    fields: Dict[str, Any]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RedisQueue:
    """Redis Streams queue wrapper with DB lifecycle mirroring."""

    def __init__(
        self,
        redis_client: Optional[object] = None,
        redis_url: Optional[str] = None,
        db_factory=SessionLocal,
    ) -> None:
        self._redis = redis_client
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._db_factory = db_factory
        self._warned = False

        if self._redis is None and self._redis_url:
            try:
                import redis  # type: ignore

                self._redis = redis.Redis.from_url(self._redis_url, decode_responses=True)
            except Exception as exc:  # pragma: no cover - defensive guard
                self._redis = None
                self._log_degraded(f"Redis client init failed: {exc}")

    @property
    def redis(self) -> object:
        if self._redis is None:
            raise RuntimeError("Redis is not configured for the job queue.")
        return self._redis

    def ensure_group(self) -> None:
        redis_client = self.redis
        try:
            redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="$", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" in str(exc):
                return
            raise

    def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        headers: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        created_at = _utc_now().isoformat()
        headers_json = json.dumps(headers)
        payload_json = json.dumps(payload)
        fields = {
            "job_id": job_id,
            "job_type": job_type,
            "payload_json": payload_json,
            "headers_json": headers_json,
            "created_at": created_at,
        }
        manage_session = db is None
        session = db or self._db_factory()
        try:
            job = BackgroundJob(
                job_id=job_id,
                job_type=job_type,
                workspace_id=_safe_int(payload.get("workspace_id")),
                status="queued",
                attempts=0,
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
            session.add(job)
            session.flush()

            if not _event_exists(session, job_id, "queued"):
                session.add(
                    BackgroundJobEvent(
                        job_id=job_id,
                        event_type="queued",
                        message="Job queued",
                        data_json={"headers": headers, "payload": payload},
                        created_at=_utc_now(),
                    )
                )

            self.ensure_group()
            entry_id = self.redis.xadd(STREAM_NAME, fields)
            job.redis_stream = STREAM_NAME
            job.redis_entry_id = entry_id
            job.updated_at = _utc_now()
            session.commit()
            return job_id
        except Exception as exc:
            session.rollback()
            if "job" in locals():
                job.status = "failed"
                job.last_error = str(exc)
                job.updated_at = _utc_now()
                session.add(job)
                session.commit()
            raise
        finally:
            if manage_session:
                session.close()

    def read_batch(self, consumer_name: str, count: int = 10, block_ms: int = 2000) -> List[QueueEntry]:
        self.ensure_group()
        response = self.redis.xreadgroup(
            CONSUMER_GROUP,
            consumer_name,
            streams={STREAM_NAME: ">"},
            count=count,
            block=block_ms,
        )
        return _parse_stream_response(response)

    def claim_stuck(
        self,
        consumer_name: str,
        min_idle_ms: int = 60000,
        count: int = 10,
    ) -> List[QueueEntry]:
        self.ensure_group()
        redis_client = self.redis
        if hasattr(redis_client, "xautoclaim"):
            _, messages = redis_client.xautoclaim(
                STREAM_NAME,
                CONSUMER_GROUP,
                consumer_name,
                min_idle_ms,
                start_id="0-0",
                count=count,
            )
            return [QueueEntry(entry_id, fields) for entry_id, fields in messages]

        pending = redis_client.xpending_range(
            STREAM_NAME,
            CONSUMER_GROUP,
            min="-",
            max="+",
            count=count,
        )
        entries: List[QueueEntry] = []
        for item in pending:
            entry_id = item["message_id"]
            idle = item["idle"]
            if idle < min_idle_ms:
                continue
            claimed = redis_client.xclaim(
                STREAM_NAME,
                CONSUMER_GROUP,
                consumer_name,
                min_idle_ms,
                [entry_id],
            )
            for claimed_entry in claimed:
                entries.append(QueueEntry(claimed_entry[0], claimed_entry[1]))
        return entries

    def ack(self, entry_id: str) -> None:
        self.redis.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)

    def send_to_dlq(self, fields: Dict[str, Any], error: str, attempts: int) -> str:
        payload = dict(fields)
        payload.update(
            {
                "error": error,
                "attempts": str(attempts),
                "last_failure_at": _utc_now().isoformat(),
            }
        )
        return self.redis.xadd(DLQ_STREAM_NAME, payload)

    def requeue(self, fields: Dict[str, Any]) -> str:
        self.ensure_group()
        return self.redis.xadd(STREAM_NAME, fields)

    def _log_degraded(self, reason: str) -> None:
        if self._warned:
            return
        logger.warning("Redis queue disabled (%s); job enqueue will fail.", reason)
        self._warned = True


def _event_exists(db: Session, job_id: str, event_type: str) -> bool:
    return (
        db.query(BackgroundJobEvent)
        .filter(BackgroundJobEvent.job_id == job_id, BackgroundJobEvent.event_type == event_type)
        .first()
        is not None
    )


def _parse_stream_response(response: Iterable) -> List[QueueEntry]:
    entries: List[QueueEntry] = []
    for stream_name, stream_entries in response or []:
        for entry_id, fields in stream_entries:
            entries.append(QueueEntry(entry_id, _decode_fields(fields)))
    return entries


def _decode_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    decoded: Dict[str, Any] = {}
    for key, value in fields.items():
        if isinstance(value, bytes):
            decoded[key] = value.decode()
        else:
            decoded[key] = value
    return decoded


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
