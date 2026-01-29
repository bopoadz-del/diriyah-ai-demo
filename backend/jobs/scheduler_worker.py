"""Scheduler worker for periodic queue enqueues."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal
from backend.hydration.models import WorkspaceSource
from backend.ops.jobs import enqueue_job, record_event
from backend.ops.models import OpsSchedule

logger = logging.getLogger(__name__)


def _ensure_nightly_hydration_schedules(db: Session) -> None:
    workspace_ids = (
        db.query(WorkspaceSource.workspace_id)
        .filter(WorkspaceSource.is_enabled == True)
        .distinct()
        .all()
    )
    now = datetime.now(timezone.utc)
    for (workspace_id,) in workspace_ids:
        name = f"nightly-hydration-{workspace_id}"
        schedule = db.query(OpsSchedule).filter(OpsSchedule.name == name).one_or_none()
        if schedule:
            continue
        schedule = OpsSchedule(
            name=name,
            workspace_id=workspace_id,
            job_type="hydration",
            is_enabled=True,
            next_run_at=now,
        )
        db.add(schedule)
    db.commit()


def process_once(
    db: Optional[Session] = None,
    redis_client: Optional[object] = None,
) -> int:
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        _ensure_nightly_hydration_schedules(db)
        now = datetime.now(timezone.utc)
        schedules = (
            db.query(OpsSchedule)
            .filter(OpsSchedule.is_enabled == True)
            .filter(OpsSchedule.next_run_at != None)
            .filter(OpsSchedule.next_run_at <= now)
            .all()
        )
        enqueued = 0
        for schedule in schedules:
            payload = {"workspace_id": schedule.workspace_id}
            headers = {"workspace_id": schedule.workspace_id, "correlation_id": f"schedule-{schedule.id}"}
            job = enqueue_job(db, schedule.job_type, payload, headers, redis_client=redis_client)
            record_event(db, job.job_id, "scheduled", data_json={"schedule_id": schedule.id})
            record_event(db, job.job_id, "enqueued", data_json={"schedule_id": schedule.id})
            schedule.last_run_at = now
            schedule.next_run_at = now + timedelta(days=1)
            enqueued += 1
        db.commit()
        return enqueued
    finally:
        if owns_session:
            db.close()


def run_worker(redis_client: Optional[object] = None) -> None:
    logging.basicConfig(level=logging.INFO)
    while True:
        count = process_once(redis_client=redis_client)
        logger.info("Scheduler tick", extra={"enqueued": count})
        if count == 0:
            time_to_sleep = 60
        else:
            time_to_sleep = 5
        time.sleep(time_to_sleep)


if __name__ == "__main__":
    run_worker()
