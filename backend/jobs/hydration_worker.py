"""Background worker for nightly hydration.

Legacy loop: prefer the Redis Streams queue worker in queue_worker.py.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.backend.db import SessionLocal, init_db
from backend.backend.pdp.audit_logger import AuditLogger
from backend.backend.pdp.policy_engine import PolicyEngine
from backend.backend.pdp.schemas import PolicyRequest
from backend.hydration.alerts import AlertManager
from backend.hydration.models import (
    AlertCategory,
    AlertSeverity,
    HydrationState,
    HydrationStatus,
    HydrationTrigger,
    WorkspaceSource,
)
from backend.hydration.pipeline import HydrationOptions, HydrationPipeline
from backend.redisx.locks import DistributedLock

logger = logging.getLogger(__name__)


def _env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    return int(value) if value is not None else default


def _env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _next_run_time(now: datetime, tz: ZoneInfo, hour: int, minute: int) -> datetime:
    local_now = now.astimezone(tz)
    scheduled = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local_now >= scheduled:
        scheduled = scheduled + timedelta(days=1)
    return scheduled.astimezone(timezone.utc)


def _evaluate_pdp(db: Session, user_id: int, workspace_id: str) -> tuple[bool, str]:
    engine = PolicyEngine(db)
    request = PolicyRequest(
        user_id=user_id,
        action="hydrate_scheduled",
        resource_type="workspace",
        resource_id=None,
        context={"project_id": workspace_id, "workspace_id": workspace_id},
    )
    decision = engine.evaluate(request)
    AuditLogger(db).log_decision(
        user_id=user_id,
        action="hydrate_scheduled",
        resource_type="workspace",
        resource_id=None,
        decision="allow" if decision.allowed else "deny",
        metadata={"reason": decision.reason, "workspace_id": workspace_id},
    )
    return decision.allowed, decision.reason


def run_worker() -> None:
    logging.basicConfig(level=logging.INFO)
    init_db()
    if not _env_bool("HYDRATION_ENABLED", True):
        logger.info("Hydration worker disabled via HYDRATION_ENABLED")
        return

    tz_name = os.getenv("HYDRATION_TZ", "Asia/Riyadh")
    poll_seconds = _env_int("HYDRATION_POLL_SECONDS", 60)
    hour = _env_int("HYDRATION_HOUR", 2)
    minute = _env_int("HYDRATION_MINUTE", 0)
    max_files = os.getenv("HYDRATION_MAX_FILES_PER_RUN")
    max_files_val = int(max_files) if max_files else None
    user_id = _env_int("HYDRATION_SERVICE_USER_ID", 0)

    tz = ZoneInfo(tz_name)

    while True:
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            sources = db.query(WorkspaceSource).filter(WorkspaceSource.is_enabled == True).all()
            for source in sources:
                state = (
                    db.query(HydrationState)
                    .filter(HydrationState.workspace_source_id == source.id)
                    .one_or_none()
                )
                if not state:
                    state = HydrationState(
                        workspace_source_id=source.id,
                        status=HydrationStatus.IDLE,
                        next_run_at=_next_run_time(now, tz, hour, minute),
                    )
                    db.add(state)
                    db.commit()
                    db.refresh(state)

                if state.next_run_at and state.next_run_at > now:
                    continue

                lock = DistributedLock()
                lock_key = f"lock:workspace:{source.workspace_id}:hydration"
                token = lock.acquire(lock_key, ttl=60 * 60 * 2, wait_seconds=0)
                if token is None:
                    continue

                try:
                    allowed, reason = _evaluate_pdp(db, user_id, source.workspace_id)
                    if not allowed:
                        state.status = HydrationStatus.FAILED
                        state.last_error = reason
                        state.consecutive_failures += 1
                        state.next_run_at = _next_run_time(now, tz, hour, minute)
                        AlertManager(db).create_alert(
                            source.workspace_id,
                            AlertSeverity.WARN,
                            AlertCategory.AUTH,
                            f"Scheduled hydration denied: {reason}",
                        )
                        db.commit()
                        continue

                    pipeline = HydrationPipeline(db)
                    options = HydrationOptions(
                        trigger=HydrationTrigger.SCHEDULED,
                        source_ids=[source.id],
                        force_full_scan=_env_bool("HYDRATION_FORCE_FULL_SCAN", False),
                        max_files=max_files_val,
                        dry_run=False,
                    )
                    pipeline.hydrate_workspace(source.workspace_id, options)
                    state.next_run_at = _next_run_time(datetime.now(timezone.utc), tz, hour, minute)
                    db.commit()
                finally:
                    lock.release(lock_key, token)
        except Exception as exc:
            logger.exception("Hydration worker loop error: %s", exc)
        finally:
            db.close()
        time.sleep(poll_seconds)


if __name__ == "__main__":
    run_worker()
