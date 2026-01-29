"""Hydration job handler wrapper."""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from backend.hydration.pipeline import HydrationOptions, HydrationPipeline, HydrationTrigger
from backend.redisx.locks import DistributedLock


def run_hydration_job(payload: Dict[str, Any], headers: Dict[str, Any], db: Session) -> Dict[str, Any]:
    workspace_id = payload["workspace_id"]
    lock = DistributedLock()
    lock_key = f"lock:workspace:{workspace_id}:hydration"
    token = lock.acquire(lock_key, ttl=60 * 60 * 2, wait_seconds=0)
    if token is None:
        return {"status": "skipped", "reason": "already running"}

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
        return {
            "status": "succeeded",
            "workspace_id": workspace_id,
            "run_id": run.id,
            "trigger": options.trigger.value,
        }
    finally:
        lock.release(lock_key, token)
