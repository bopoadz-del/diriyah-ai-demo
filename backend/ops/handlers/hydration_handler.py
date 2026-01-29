"""Hydration job handler for the queue worker."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from sqlalchemy.orm import Session

from backend.hydration.models import HydrationTrigger
from backend.hydration.pipeline import HydrationOptions, HydrationPipeline
from backend.redisx.locks import DistributedLock


def handle_hydration(payload: Dict[str, object], headers: Dict[str, object], db: Session) -> Dict[str, object]:
    workspace_id = payload.get("workspace_id") or headers.get("workspace_id")
    if not workspace_id:
        raise ValueError("workspace_id is required for hydration jobs")

    lock = DistributedLock()
    lock_key = f"lock:workspace:{workspace_id}:hydration"
    token = lock.acquire(lock_key, ttl=60 * 60 * 2, wait_seconds=0)
    if token is None:
        return {
            "status": "skipped",
            "reason": "already running",
            "workspace_id": workspace_id,
            "skipped_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        pipeline = HydrationPipeline(db)
        options = HydrationOptions(
            trigger=HydrationTrigger.API,
            source_ids=payload.get("source_ids"),
            force_full_scan=bool(payload.get("force_full_scan", False)),
            max_files=payload.get("max_files"),
            dry_run=bool(payload.get("dry_run", False)),
        )
        run = pipeline.hydrate_workspace(str(workspace_id), options)
    finally:
        lock.release(lock_key, token)

    return {
        "status": str(run.status.value if hasattr(run.status, "value") else run.status),
        "run_id": run.id,
        "workspace_id": run.workspace_id,
        "files_seen": run.files_seen,
        "files_indexed": run.files_indexed,
        "files_failed": run.files_failed,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }
