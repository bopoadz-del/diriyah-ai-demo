"""Helpers for background job lifecycle management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.ops.models import BackgroundJob, BackgroundJobEvent
from backend.redisx import queue


def _get_workspace_id(payload: dict, headers: dict) -> Optional[str]:
    return payload.get("workspace_id") or headers.get("workspace_id")


def ensure_job(
    db: Session,
    job_id: str,
    job_type: str,
    payload: dict,
    headers: dict,
    redis_entry_id: Optional[str] = None,
    status: str = "queued",
) -> BackgroundJob:
    job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).one_or_none()
    if job:
        if redis_entry_id and not job.redis_entry_id:
            job.redis_entry_id = redis_entry_id
        if job.status != status and job.status == "queued":
            job.status = status
        db.commit()
        return job

    job = BackgroundJob(
        job_id=job_id,
        job_type=job_type,
        workspace_id=_get_workspace_id(payload, headers),
        status=status,
        redis_stream=queue.STREAM_NAME,
        redis_entry_id=redis_entry_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    record_event(
        db,
        job_id,
        "queued",
        data_json={"queued_at": datetime.now(timezone.utc).isoformat()},
        dedupe_queued=True,
    )
    return job


def enqueue_job(
    db: Session,
    job_type: str,
    payload: dict,
    headers: dict,
    redis_client: Optional[object] = None,
) -> BackgroundJob:
    job_id, entry_id = queue.enqueue_with_entry_id(
        job_type,
        payload,
        headers,
        redis_client=redis_client,
    )
    job = ensure_job(
        db,
        job_id,
        job_type,
        payload,
        headers,
        redis_entry_id=entry_id,
        status="queued",
    )
    return job


def record_event(
    db: Session,
    job_id: str,
    event_type: str,
    message: Optional[str] = None,
    data_json: Optional[dict] = None,
    dedupe_queued: bool = False,
) -> None:
    if dedupe_queued and event_type == "queued":
        exists = (
            db.query(BackgroundJobEvent)
            .filter(
                BackgroundJobEvent.job_id == job_id,
                BackgroundJobEvent.event_type == event_type,
            )
            .first()
        )
        if exists:
            return
    event = BackgroundJobEvent(
        job_id=job_id,
        event_type=event_type,
        message=message,
        data_json=data_json,
    )
    db.add(event)
    db.commit()


def update_job_status(
    db: Session,
    job: BackgroundJob,
    status: str,
    result_json: Optional[dict] = None,
    last_error: Optional[str] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
) -> None:
    job.status = status
    if result_json is not None:
        job.result_json = result_json
    if last_error is not None:
        job.last_error = last_error
    if started_at is not None:
        job.started_at = started_at
    if finished_at is not None:
        job.finished_at = finished_at
    db.commit()
