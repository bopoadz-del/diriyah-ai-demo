"""Redis Streams queue worker for background jobs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import socket
import time
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal
from backend.ops.handlers.hydration_handler import handle_hydration_job
from backend.ops.models import BackgroundJob, BackgroundJobEvent
from backend.redisx.queue import CONSUMER_GROUP, STREAM_NAME, RedisQueue, QueueEntry

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BACKOFF_SECONDS = [5, 15, 60, 180, 600]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _consumer_name() -> str:
    return os.getenv("HOSTNAME") or f"worker-{socket.gethostname()}-{os.getpid()}"


def _decode_json(payload: str | dict | None) -> Dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {}


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _record_event(
    db: Session,
    job_id: str,
    event_type: str,
    message: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    db.add(
        BackgroundJobEvent(
            job_id=job_id,
            event_type=event_type,
            message=message,
            data_json=data,
            created_at=_utc_now(),
        )
    )


def _emit_hydration_event(
    db: Session,
    event_type: str,
    job: BackgroundJob,
    payload: Dict[str, Any],
    headers: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    event_payload = {"job_id": job.job_id, "job_type": job.job_type, **(extra or {})}
    event = EventEnvelope.build(
        event_type=event_type,
        source="hydration",
        payload=event_payload,
        workspace_id=job.workspace_id,
        actor_id=_safe_int(headers.get("user_id")),
        correlation_id=headers.get("correlation_id"),
    )
    _emitter.emit_global(event, db=db)
    if job.workspace_id is not None:
        _emitter.emit_workspace(job.workspace_id, event, db=db)


def _get_job(db: Session, job_id: str) -> Optional[BackgroundJob]:
    return db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).one_or_none()


def _mark_running(job: BackgroundJob) -> None:
    job.status = "running"
    if job.started_at is None:
        job.started_at = _utc_now()
    job.updated_at = _utc_now()


def _mark_success(job: BackgroundJob, result: Dict[str, Any]) -> None:
    job.status = "success"
    job.result_json = result
    job.finished_at = _utc_now()
    job.updated_at = _utc_now()


def _mark_failed(job: BackgroundJob, error: str) -> None:
    job.status = "failed"
    job.last_error = error
    job.updated_at = _utc_now()


def _mark_dlq(job: BackgroundJob, error: str) -> None:
    job.status = "dlq"
    job.last_error = error
    job.finished_at = _utc_now()
    job.updated_at = _utc_now()


def _handle_entry(
    entry: QueueEntry,
    queue: RedisQueue,
    db: Session,
    hydration_handler: Callable[[BackgroundJob, Dict[str, Any], Dict[str, Any], Session], Dict[str, Any]],
    sleep_fn: Callable[[float], None],
) -> None:
    fields = dict(entry.fields)
    job_id = fields.get("job_id")
    job_type = fields.get("job_type")
    payload = _decode_json(fields.get("payload_json"))
    headers = _decode_json(fields.get("headers_json"))

    if not job_id or not job_type:
        logger.warning("Invalid queue entry %s missing job_id/job_type", entry.entry_id)
        queue.ack(STREAM_NAME, CONSUMER_GROUP, entry.entry_id)
        return

    job = _get_job(db, job_id)
    if job is None:
        job = BackgroundJob(
            job_id=job_id,
            job_type=job_type,
            workspace_id=_safe_int(payload.get("workspace_id")),
            status="queued",
            attempts=0,
            redis_stream=STREAM_NAME,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        db.add(job)
        _record_event(db, job_id, "queued", "Job discovered by worker", data={"payload": payload})
        db.commit()

    _record_event(db, job_id, "received", "Job received")

    if job.status in {"success", "dlq"}:
        db.commit()
        queue.ack(STREAM_NAME, CONSUMER_GROUP, entry.entry_id)
        return

    _mark_running(job)
    job.redis_entry_id = entry.entry_id
    _record_event(db, job_id, "started", "Job processing started")
    db.commit()
    _emit_hydration_event(
        db,
        "hydration.started",
        job,
        payload,
        headers,
        extra={"attempt": job.attempts + 1},
    )

    try:
        if job_type != "hydration":
            raise ValueError(f"Unsupported job type {job_type}")

        result = hydration_handler(job, payload, headers, db)
        _mark_success(job, result)
        _record_event(db, job_id, "completed", "Job completed", data=result)
        db.commit()
        queue.ack(STREAM_NAME, CONSUMER_GROUP, entry.entry_id)
    except Exception as exc:
        error_message = str(exc)
        job.attempts += 1
        _mark_failed(job, error_message)
        _record_event(db, job_id, "failed_attempt", error_message, data={"attempt": job.attempts})
        db.commit()
        _emit_hydration_event(
            db,
            "hydration.failed",
            job,
            payload,
            headers,
            extra={"attempt": job.attempts, "error": error_message},
        )

        if job.attempts >= MAX_ATTEMPTS:
            queue.ack(STREAM_NAME, CONSUMER_GROUP, entry.entry_id)
            queue.add_to_dlq(fields, error_message)
            _mark_dlq(job, error_message)
            _record_event(db, job_id, "dlq", "Job moved to DLQ")
            db.commit()
            return

        backoff = BACKOFF_SECONDS[min(job.attempts - 1, len(BACKOFF_SECONDS) - 1)]
        fields["attempt"] = str(job.attempts)
        job.status = "queued"
        job.updated_at = _utc_now()
        _record_event(db, job_id, "retrying", f"Retrying in {backoff}s", data={"attempt": job.attempts})
        db.commit()
        queue.ack(STREAM_NAME, CONSUMER_GROUP, entry.entry_id)
        sleep_fn(backoff)
        queue.requeue(fields)


def process_once(
    queue: RedisQueue,
    db_factory=SessionLocal,
    hydration_handler: Callable[[BackgroundJob, Dict[str, Any], Dict[str, Any], Session], Dict[str, Any]] = handle_hydration_job,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    consumer = _consumer_name()
    queue.ensure_group(STREAM_NAME, CONSUMER_GROUP)

    claimed = queue.claim(STREAM_NAME, CONSUMER_GROUP, consumer=consumer, min_idle_ms=60000)
    entries = claimed + queue.read(STREAM_NAME, CONSUMER_GROUP, consumer=consumer, count=10, block_ms=100)

    processed = 0
    for entry in entries:
        db = db_factory()
        try:
            _handle_entry(entry, queue, db, hydration_handler, sleep_fn)
            processed += 1
        finally:
            db.close()
    return processed


def run_forever() -> None:
    queue = RedisQueue()
    consumer = _consumer_name()
    queue.ensure_group(STREAM_NAME, CONSUMER_GROUP)

    logger.info("Queue worker starting", extra={"consumer": consumer})

    while True:
        try:
            claimed = queue.claim(STREAM_NAME, CONSUMER_GROUP, consumer=consumer, min_idle_ms=60000)
            entries = claimed + queue.read(STREAM_NAME, CONSUMER_GROUP, consumer=consumer, count=10, block_ms=2000)
            if not entries:
                continue
            for entry in entries:
                db = SessionLocal()
                try:
                    _handle_entry(entry, queue, db, handle_hydration_job, time.sleep)
                finally:
                    db.close()
        except Exception as exc:
            logger.exception("Queue worker loop error: %s", exc)
            time.sleep(1)


if __name__ == "__main__":
    run_forever()
