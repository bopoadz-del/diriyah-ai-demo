"""Redis Streams queue worker for background jobs."""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal
from backend.ops.handlers.hydration_handler import handle_hydration
from backend.ops.jobs import ensure_job, record_event
from backend.ops.models import BackgroundJob
from backend.redisx import queue

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BACKOFF_SECONDS = [5, 15, 45, 120, 300]


def _consumer_name() -> str:
    return f"worker-{socket.gethostname()}-{os.getpid()}"


def _parse_payload(fields: Dict[str, str]) -> Dict[str, object]:
    payload_json = fields.get("payload_json") or "{}"
    headers_json = fields.get("headers_json") or "{}"
    payload = json.loads(payload_json)
    headers = json.loads(headers_json)
    return {"payload": payload, "headers": headers}


def _mark_running(db: Session, job: BackgroundJob, attempts: int) -> None:
    now = datetime.now(timezone.utc)
    job.status = "running"
    job.attempts = attempts
    job.started_at = job.started_at or now
    job.updated_at = now
    db.commit()
    record_event(db, job.job_id, "started", data_json={"attempt": attempts, "started_at": now.isoformat()})


def _mark_retry(db: Session, job: BackgroundJob, attempts: int, error: str, backoff: int) -> None:
    job.status = "queued"
    job.last_error = error
    job.attempts = attempts
    db.commit()
    record_event(
        db,
        job.job_id,
        "retrying",
        message=error,
        data_json={"attempt": attempts, "backoff_seconds": backoff},
    )


def _mark_failed(db: Session, job: BackgroundJob, error: str, event_type: str) -> None:
    now = datetime.now(timezone.utc)
    job.status = event_type
    job.last_error = error
    job.finished_at = now
    db.commit()
    record_event(db, job.job_id, event_type, message=error, data_json={"finished_at": now.isoformat()})


def _mark_succeeded(db: Session, job: BackgroundJob, result: dict) -> None:
    now = datetime.now(timezone.utc)
    job.status = "succeeded"
    job.result_json = result
    job.finished_at = now
    db.commit()
    record_event(db, job.job_id, "succeeded", data_json={"finished_at": now.isoformat()})


def _handle_job(
    entry_id: str,
    fields: Dict[str, str],
    redis_client: Optional[object],
    db_session_factory,
) -> None:
    job_id = fields.get("job_id")
    job_type = fields.get("job_type")
    if not job_id or not job_type:
        logger.warning("Skipping job with missing id/type: %s", fields)
        queue.ack(entry_id, redis_client=redis_client)
        return

    parsed = _parse_payload(fields)
    payload = parsed["payload"]
    headers = parsed["headers"]

    db = db_session_factory()
    try:
        job = ensure_job(
            db,
            job_id,
            job_type,
            payload,
            headers,
            redis_entry_id=entry_id,
            status="queued",
        )
        if job.status in {"succeeded", "dlq"}:
            queue.ack(entry_id, redis_client=redis_client)
            return

        for attempt in range(job.attempts + 1, MAX_ATTEMPTS + 1):
            _mark_running(db, job, attempt)
            try:
                if job_type != "hydration":
                    raise ValueError(f"Unsupported job type: {job_type}")
                result = handle_hydration(payload, headers, db)
            except Exception as exc:
                error = str(exc)
                backoff_index = min(attempt - 1, len(BACKOFF_SECONDS) - 1)
                backoff = BACKOFF_SECONDS[backoff_index]
                if attempt >= MAX_ATTEMPTS:
                    queue.send_to_dlq(fields, error, attempt, redis_client=redis_client)
                    _mark_failed(db, job, error, "dlq")
                    queue.ack(entry_id, redis_client=redis_client)
                    return
                _mark_retry(db, job, attempt, error, backoff)
                time.sleep(backoff)
                continue
            else:
                _mark_succeeded(db, job, result)
                queue.ack(entry_id, redis_client=redis_client)
                return
    finally:
        db.close()


def process_once(
    redis_client: Optional[object] = None,
    db_session_factory=SessionLocal,
    consumer_name: Optional[str] = None,
) -> int:
    consumer = consumer_name or _consumer_name()
    queue.ensure_group(redis_client=redis_client)
    processed = 0

    for entry_id, fields in queue.claim_stuck(
        consumer,
        redis_client=redis_client,
    ):
        _handle_job(entry_id, fields, redis_client, db_session_factory)
        processed += 1

    for entry_id, fields in queue.read_batch(
        consumer,
        redis_client=redis_client,
    ):
        _handle_job(entry_id, fields, redis_client, db_session_factory)
        processed += 1

    return processed


def run_worker(redis_client: Optional[object] = None) -> None:
    logging.basicConfig(level=logging.INFO)
    consumer = _consumer_name()
    logger.info("Starting queue worker", extra={"consumer": consumer})
    while True:
        processed = process_once(redis_client=redis_client, consumer_name=consumer)
        if processed == 0:
            time.sleep(1)


if __name__ == "__main__":
    run_worker()
