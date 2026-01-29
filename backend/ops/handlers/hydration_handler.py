"""Hydration job handler wrapper."""

from __future__ import annotations

import time
from typing import Any, Dict

from sqlalchemy.orm import Session

from backend.hydration.pipeline import HydrationOptions, HydrationPipeline, HydrationTrigger
from backend.redisx.locks import DistributedLock


def handle_hydration_job(job: Any, payload: Dict[str, Any], headers: Dict[str, Any], db: Session) -> Dict[str, Any]:
    workspace_id = payload["workspace_id"]
    lock = DistributedLock()
    lock_key = f"lock:workspace:{workspace_id}:hydration"
    token = lock.acquire(lock_key, ttl=60 * 60 * 2, wait_seconds=0)
    if token is None:
        return {"skipped": "already_running"}

    start_time = time.monotonic()
    correlation_id = headers.get("correlation_id")

    try:
        pipeline = HydrationPipeline(db)
        options = HydrationOptions(
            trigger=HydrationTrigger.API,
            source_ids=payload.get("source_ids"),
            force_full_scan=bool(payload.get("force_full_scan")),
            max_files=payload.get("max_files"),
            dry_run=bool(payload.get("dry_run")),
        )
        run = pipeline.hydrate_workspace(workspace_id, options)
        duration_sec = round(time.monotonic() - start_time, 3)
        return {
            "files_scanned": run.files_seen,
            "docs_added": run.files_new,
            "embeddings_added": run.files_indexed,
            "duration_sec": duration_sec,
            "correlation_id": correlation_id,
            "workspace_id": workspace_id,
            "run_id": run.id,
        }
    finally:
        lock.release(lock_key, token)
