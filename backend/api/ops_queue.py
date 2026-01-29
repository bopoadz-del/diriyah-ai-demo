"""Ops queue endpoints for Redis Streams jobs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.ops.models import BackgroundJob
from backend.redisx import queue

router = APIRouter(prefix="/ops/queue", tags=["Ops Queue"])


@router.get("/stats")
def queue_stats() -> dict:
    return queue.stats()


@router.post("/jobs/{job_id}/replay")
def replay_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    new_job_id = queue.replay_from_dlq(job_id=job_id, db=db)
    if not new_job_id:
        raise HTTPException(status_code=404, detail="Job not found in DLQ")
    return {"job_id": new_job_id, "status": "requeued"}


@router.get("/jobs/dlq")
def list_dlq(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    entries = queue.get_dlq_entries(limit=limit)
    return {"entries": entries}
