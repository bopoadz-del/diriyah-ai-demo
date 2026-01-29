"""Ops API for background job inspection."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.ops.models import BackgroundJob, BackgroundJobEvent

router = APIRouter(prefix="/ops/jobs", tags=["Ops Jobs"])


def _job_to_dict(job: BackgroundJob) -> dict:
    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "workspace_id": job.workspace_id,
        "status": job.status,
        "attempts": job.attempts,
        "last_error": job.last_error,
        "result_json": job.result_json,
        "redis_stream": job.redis_stream,
        "redis_entry_id": job.redis_entry_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


def _event_to_dict(event: BackgroundJobEvent) -> dict:
    return {
        "id": event.id,
        "job_id": event.job_id,
        "event_type": event.event_type,
        "message": event.message,
        "data_json": event.data_json,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_dict(job)


@router.get("")
def list_jobs(
    status: Optional[str] = Query(default=None),
    workspace_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[dict]:
    query = db.query(BackgroundJob)
    if status:
        query = query.filter(BackgroundJob.status == status)
    if workspace_id:
        query = query.filter(BackgroundJob.workspace_id == workspace_id)
    jobs = query.order_by(BackgroundJob.created_at.desc()).limit(limit).all()
    return [_job_to_dict(job) for job in jobs]


@router.get("/{job_id}/events")
def job_events(job_id: str, db: Session = Depends(get_db)) -> List[dict]:
    events = (
        db.query(BackgroundJobEvent)
        .filter(BackgroundJobEvent.job_id == job_id)
        .order_by(BackgroundJobEvent.created_at.asc())
        .all()
    )
    return [_event_to_dict(event) for event in events]
