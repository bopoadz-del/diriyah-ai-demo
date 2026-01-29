"""Redis Streams queue worker for background jobs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import socket
import time
from typing import Any, Callable, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal
from backend.ops.handlers.hydration_handler import run_hydration_job
from backend.ops.models import BackgroundJob, BackgroundJobEvent
from backend.redisx.queue import RedisQueue, QueueEntry

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BACKOFF_SECONDS = [5, 15, 45, 120, 300]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _consumer_name() -> str:
    return f"worker-{socket.gethostname()}-{os.getpid()}"


def _decode_json(payload: str | dict | None) -> Dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {}


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


def _get_job(db: Session, job_id: str) -> Optional[BackgroundJob]:
    return db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).one_or_none()


def _update_job_running(job: BackgroundJob) -> None:
    job.status = "running"
    job.attempts += 1
    if job.started_at is None:
        job.started_at = _utc_now()
    job.updated_at = _utc_now()


def _update_job_success(job: BackgroundJob, result: Dict[str, Any]) -> None:
    job.status = "succeeded"
    job.result_json = result
    job.finished_at = _utc_now()
    job.updated_at = _utc_now()


def _update_job_failure(job: BackgroundJob, error: str) -> None:
    job.status = "failed"
    job.last_error = error
    job.updated_at = _utc_now()


def _update_job_dlq(job: BackgroundJob, error: str) -> None:
    job.status = "dlq"
    job.last_error = error
    job.finished_at = _utc_now()
    job.updated_at = _utc_now()


def _handle_entry(
    entry: QueueEntry,
    queue: RedisQueue,
    db: Session,
    hydration_handler: Callable[[Dict[str, Any], Dict[str, Any], Session], Dict[str, Any]],
    sleep_fn: Callable[[float], None],
) -> None:
    fields = entry.fields
    job_id = fields.get("job_id")
    job_type = fields.get("job_type")
    payload = _decode_json(fields.get("payload_json"))
    headers = _decode_json(fields.get("headers_json"))

    if not job_id or not job_type:
        logger.warning("Invalid queue entry %s missing job_id/job_type", entry.entry_id)
        queue.ack(entry.entry_id)
        return

    job = _get_job(db, job_id)
    if job is None:
        job = BackgroundJob(
            job_id=job_id,
            job_type=job_type,
            workspace_id=payload.get("workspace_id"),
            status="queued",
            attempts=0,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        db.add(job)
        _record_event(db, job_id, "queued", "Job discovered by worker", data={"payload": payload})
        db.commit()

    if job.status in {"succeeded", "dlq"}:
        queue.ack(entry.entry_id)
        return

    _update_job_running(job)
    _record_event(db, job_id, "started", "Job processing started")
    job.redis_entry_id = entry.entry_id
    db.commit()

    try:
        if job_type != "hydration":
            raise ValueError(f"Unsupported job type {job_type}")

        result = hydration_handler(payload, headers, db)
        _update_job_success(job, result)
        _record_event(db, job_id, "succeeded", "Job completed", data=result)
        db.commit()
        queue.ack(entry.entry_id)
    except Exception as exc:
        error_message = str(exc)
        _update_job_failure(job, error_message)
        _record_event(db, job_id, "failed", error_message)
        db.commit()

        if job.attempts < MAX_ATTEMPTS:
            backoff = BACKOFF_SECONDS[min(job.attempts - 1, len(BACKOFF_SECONDS) - 1)]
            _record_event(db, job_id, "retrying", f"Retrying in {backoff}s")
            job.status = "queued"
            job.updated_at = _utc_now()
            db.commit()
            queue.ack(entry.entry_id)
            sleep_fn(backoff)
            queue.requeue(fields)
        else:
            queue.ack(entry.entry_id)
            queue.send_to_dlq(fields, error_message, job.attempts)
            _update_job_dlq(job, error_message)
            _record_event(db, job_id, "dlq", "Job moved to DLQ")
            db.commit()


def process_once(
    queue: RedisQueue,
    db_factory=SessionLocal,
    hydration_handler: Callable[[Dict[str, Any], Dict[str, Any], Session], Dict[str, Any]] = run_hydration_job,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    consumer = _consumer_name()
    queue.ensure_group()

    claimed = queue.claim_stuck(consumer_name=consumer, min_idle_ms=60000, count=10)
    entries = claimed + queue.read_batch(consumer_name=consumer, count=10, block_ms=100)

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
    queue.ensure_group()

    logger.info("Queue worker starting", extra={"consumer": consumer})

    while True:
        try:
            claimed = queue.claim_stuck(consumer_name=consumer, min_idle_ms=60000, count=10)
            entries = claimed + queue.read_batch(consumer_name=consumer, count=10, block_ms=2000)
            if not entries:
                continue
            for entry in entries:
                db = SessionLocal()
                try:
                    _handle_entry(entry, queue, db, run_hydration_job, time.sleep)
                finally:
                    db.close()
        except Exception as exc:
            logger.exception("Queue worker loop error: %s", exc)
            time.sleep(1)


if __name__ == "__main__":
    run_forever()
