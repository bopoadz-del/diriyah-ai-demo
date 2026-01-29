"""Redis Streams-backed job queue helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
import socket
import uuid
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal
from backend.ops.models import BackgroundJob, BackgroundJobEvent

logger = logging.getLogger(__name__)

STREAM_NAME = "jobs:main"
DLQ_STREAM_NAME = "jobs:dlq"
CONSUMER_GROUP = "workers"


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

    def connect(self) -> object:
        if self._redis is not None:
            return self._redis
        if not self._redis_url:
            raise RuntimeError("REDIS_URL is not configured for the job queue.")
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(self._redis_url, decode_responses=True)
            if hasattr(client, "ping"):
                client.ping()
            self._redis = client
            return client
        except Exception as exc:
            raise RuntimeError(f"Redis unavailable for job queue: {exc}") from exc

    @property
    def redis(self) -> object:
        return self.connect()

    def ensure_group(self, stream: str = STREAM_NAME, group: str = CONSUMER_GROUP) -> None:
        redis_client = self.redis
        try:
            redis_client.xgroup_create(stream, group, id="$", mkstream=True)
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
        job_id = str(headers.get("job_id") or uuid.uuid4())
        created_at = _utc_now().isoformat()
        payload_json = json.dumps(payload)
        headers_json = json.dumps(headers)
        workspace_id = _safe_int(payload.get("workspace_id"))
        fields = {
            "job_id": job_id,
            "job_type": job_type,
            "workspace_id": str(workspace_id) if workspace_id is not None else "",
            "payload_json": payload_json,
            "headers_json": headers_json,
            "attempt": "0",
            "created_at": created_at,
        }
        manage_session = db is None
        session = db or self._db_factory()
        try:
            job = BackgroundJob(
                job_id=job_id,
                job_type=job_type,
                workspace_id=workspace_id,
                status="queued",
                attempts=0,
                redis_stream=STREAM_NAME,
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
            session.add(job)
            session.flush()
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

    def read(
        self,
        stream: str = STREAM_NAME,
        group: str = CONSUMER_GROUP,
        consumer: Optional[str] = None,
        count: int = 1,
        block_ms: int = 2000,
    ) -> List[QueueEntry]:
        self.ensure_group(stream, group)
        consumer_name = consumer or os.getenv("HOSTNAME") or socket.gethostname()
        response = self.redis.xreadgroup(
            group,
            consumer_name,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )
        return _parse_stream_response(response)

    def claim(
        self,
        stream: str = STREAM_NAME,
        group: str = CONSUMER_GROUP,
        consumer: Optional[str] = None,
        min_idle_ms: int = 60000,
        entry_ids: Optional[List[str]] = None,
    ) -> List[QueueEntry]:
        self.ensure_group(stream, group)
        consumer_name = consumer or os.getenv("HOSTNAME") or socket.gethostname()
        redis_client = self.redis

        if hasattr(redis_client, "xautoclaim"):
            _, messages = redis_client.xautoclaim(
                stream,
                group,
                consumer_name,
                min_idle_ms,
                start_id="0-0",
                count=len(entry_ids) if entry_ids else 10,
            )
            return [QueueEntry(entry_id, _decode_fields(fields)) for entry_id, fields in messages]

        if entry_ids is None:
            pending = redis_client.xpending_range(
                stream,
                group,
                min="-",
                max="+",
                count=10,
            )
            entry_ids = [item["message_id"] for item in pending]

        entries: List[QueueEntry] = []
        if entry_ids:
            claimed = redis_client.xclaim(
                stream,
                group,
                consumer_name,
                min_idle_ms,
                entry_ids,
            )
            for entry_id, fields in claimed:
                entries.append(QueueEntry(entry_id, _decode_fields(fields)))
        return entries

    def ack(self, stream: str, group: str, entry_id: str) -> None:
        self.redis.xack(stream, group, entry_id)

    def add_to_dlq(self, fields: Dict[str, Any], error: str) -> str:
        payload = dict(fields)
        payload.update(
            {
                "error": error,
                "failed_at": _utc_now().isoformat(),
            }
        )
        return self.redis.xadd(DLQ_STREAM_NAME, payload)

    def requeue(self, fields: Dict[str, Any]) -> str:
        self.ensure_group()
        return self.redis.xadd(STREAM_NAME, fields)


def _parse_stream_response(response: Iterable) -> List[QueueEntry]:
    entries: List[QueueEntry] = []
    for _stream_name, stream_entries in response or []:
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
