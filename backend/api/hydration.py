"""API endpoints for hydration pipeline."""

from __future__ import annotations

import json
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.backend.pdp.audit_logger import AuditLogger
from backend.backend.pdp.policy_engine import PolicyEngine
from backend.backend.pdp.schemas import PolicyRequest
from backend.hydration.alerts import AlertManager
from backend.hydration.models import (
    AlertCategory,
    AlertSeverity,
    HydrationAlert,
    HydrationRun,
    HydrationRunItem,
    HydrationState,
    HydrationStatus,
    SourceType,
    WorkspaceSource,
)
from backend.hydration.schemas import (
    HydrationAlertOut,
    HydrationRunItemOut,
    HydrationRunOut,
    HydrationStatusOut,
    RunNowRequest,
    WorkspaceSourceCreate,
    WorkspaceSourceOut,
    WorkspaceSourceUpdate,
)
from backend.redisx.queue import RedisQueue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hydration", tags=["Hydration"])


def _parse_user_id(x_user_id: Optional[str]) -> Optional[int]:
    """Parse X-User-Id header, returning None for anonymous requests."""
    if not x_user_id:
        return None
    try:
        return int(x_user_id)
    except ValueError:
        return None


def _evaluate_pdp(db: Session, user_id: Optional[int], action: str, workspace_id: str) -> None:
    """Evaluate PDP policy. If user_id is None, skip PDP (anonymous allowed)."""
    if user_id is None:
        # Anonymous request - skip PDP evaluation, allow by default
        logger.debug("Anonymous request to %s for workspace %s - skipping PDP", action, workspace_id)
        return
    engine = PolicyEngine(db)
    request = PolicyRequest(
        user_id=user_id,
        action=action,
        resource_type="workspace",
        resource_id=None,
        context={"project_id": workspace_id, "workspace_id": workspace_id},
    )
    decision = engine.evaluate(request)
    AuditLogger(db).log_decision(
        user_id=user_id,
        action=action,
        resource_type="workspace",
        resource_id=None,
        decision="allow" if decision.allowed else "deny",
        metadata={"reason": decision.reason, "workspace_id": workspace_id},
    )
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)


@router.get("/status", response_model=HydrationStatusOut)
def hydration_status(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
) -> HydrationStatusOut:
    states = (
        db.query(HydrationState)
        .join(WorkspaceSource, WorkspaceSource.id == HydrationState.workspace_source_id)
        .filter(WorkspaceSource.workspace_id == workspace_id)
        .all()
    )
    last_run_at = max((state.last_run_at for state in states if state.last_run_at), default=None)
    next_run_at = min((state.next_run_at for state in states if state.next_run_at), default=None)
    status_value = HydrationStatus.IDLE
    if any(state.status == HydrationStatus.RUNNING for state in states):
        status_value = HydrationStatus.RUNNING
    elif any(state.status == HydrationStatus.FAILED for state in states):
        status_value = HydrationStatus.FAILED

    alerts = (
        db.query(HydrationAlert)
        .filter(HydrationAlert.workspace_id == workspace_id, HydrationAlert.is_active == True)
        .order_by(HydrationAlert.created_at.desc())
        .all()
    )
    runs = (
        db.query(HydrationRun)
        .filter(HydrationRun.workspace_id == workspace_id)
        .order_by(HydrationRun.started_at.desc())
        .limit(5)
        .all()
    )
    last_error = None
    if states:
        last_error = next((state.last_error for state in states if state.last_error), None)

    return HydrationStatusOut(
        workspace_id=workspace_id,
        last_run_at=last_run_at,
        next_run_at=next_run_at,
        status=status_value,
        last_error=last_error,
        alerts=[HydrationAlertOut.model_validate(alert) for alert in alerts],
        recent_runs=[HydrationRunOut.model_validate(run) for run in runs],
    )


@router.post("/run-now", status_code=status.HTTP_202_ACCEPTED)
def run_now(
    request: RunNowRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
):
    """Trigger a hydration run for the specified workspace.

    Returns 202 on success with job_id, or appropriate error codes:
    - 400: No hydration sources configured
    - 403: PDP policy denied
    - 500: Unexpected server error (logged with traceback)
    - 503: Redis/queue unavailable
    """
    user_id = _parse_user_id(x_user_id)
    correlation_id = x_correlation_id or os.getenv("CORRELATION_ID") or str(uuid.uuid4())

    try:
        # PDP authorization check
        try:
            _evaluate_pdp(db, user_id, "hydrate_run_now", request.workspace_id)
        except HTTPException as exc:
            AlertManager(db).create_alert(
                request.workspace_id,
                AlertSeverity.WARN,
                AlertCategory.AUTH,
                f"Manual hydration denied: {exc.detail}",
            )
            raise

        # Check that at least one enabled source exists for this workspace
        def _get_enabled_sources():
            query = db.query(WorkspaceSource).filter(
                WorkspaceSource.workspace_id == request.workspace_id,
                WorkspaceSource.is_enabled == True,
            )
            if request.source_ids:
                query = query.filter(WorkspaceSource.id.in_(request.source_ids))
            return query.all()

        enabled_sources = _get_enabled_sources()

        # Auto-seed demo source for "demo" workspace if no sources exist
        if not enabled_sources and request.workspace_id == DEMO_WORKSPACE_ID:
            logger.info("No sources for demo workspace, auto-seeding demo source")
            try:
                seed_demo_source(db)
                enabled_sources = _get_enabled_sources()
            except Exception as seed_exc:
                logger.warning("Failed to auto-seed demo source: %s", seed_exc)

        if not enabled_sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No hydration sources configured for workspace {request.workspace_id}",
            )

        # Enqueue the hydration job
        queue = RedisQueue()
        payload = {
            "workspace_id": request.workspace_id,
            "source_ids": request.source_ids,
            "force_full_scan": request.force_full_scan,
            "max_files": request.max_files,
            "dry_run": request.dry_run,
        }
        headers = {
            "correlation_id": correlation_id,
            "workspace_id": request.workspace_id,
            "user_id": user_id,
        }
        try:
            job_id = queue.enqueue("hydration", payload, headers, db=db)
        except RuntimeError as exc:
            logger.error(
                "Redis queue unavailable for hydration run: %s",
                exc,
                extra={"correlation_id": correlation_id, "workspace_id": request.workspace_id},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Queue service unavailable: {exc}",
            ) from exc

        return {"job_id": job_id, "status": "queued"}

    except HTTPException:
        # Re-raise HTTP exceptions as-is (400, 403, 503)
        raise
    except Exception as exc:
        # Catch-all for unexpected errors - log with traceback and return 500
        tb = traceback.format_exc()
        logger.error(
            "Unexpected error in run-now endpoint: %s\n%s",
            exc,
            tb,
            extra={
                "correlation_id": correlation_id,
                "workspace_id": request.workspace_id,
                "user_id": user_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {type(exc).__name__}: {exc}",
        ) from exc


@router.get("/runs", response_model=List[HydrationRunOut])
def list_runs(
    workspace_id: str = Query(...),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[HydrationRunOut]:
    runs = (
        db.query(HydrationRun)
        .filter(HydrationRun.workspace_id == workspace_id)
        .order_by(HydrationRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [HydrationRunOut.model_validate(run) for run in runs]


@router.get("/runs/{run_id}", response_model=HydrationRunOut)
def get_run(run_id: int, db: Session = Depends(get_db)) -> HydrationRunOut:
    run = db.query(HydrationRun).filter(HydrationRun.id == run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return HydrationRunOut.model_validate(run)


@router.get("/runs/{run_id}/items", response_model=List[HydrationRunItemOut])
def get_run_items(run_id: int, db: Session = Depends(get_db)) -> List[HydrationRunItemOut]:
    items = db.query(HydrationRunItem).filter(HydrationRunItem.run_id == run_id).all()
    return [HydrationRunItemOut.model_validate(item) for item in items]


@router.post("/sources", response_model=WorkspaceSourceOut, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: WorkspaceSourceCreate,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    user_id = _parse_user_id(x_user_id)
    _evaluate_pdp(db, user_id, "hydrate_manage_sources", payload.workspace_id)
    source = WorkspaceSource(
        workspace_id=payload.workspace_id,
        source_type=payload.source_type,
        name=payload.name,
        config_json=json.dumps(payload.config_json),
        secrets_ref=payload.secrets_ref,
        is_enabled=payload.is_enabled,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return WorkspaceSourceOut.model_validate(source)


@router.put("/sources/{source_id}", response_model=WorkspaceSourceOut)
def update_source(
    source_id: int,
    payload: WorkspaceSourceUpdate,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    source = db.query(WorkspaceSource).filter(WorkspaceSource.id == source_id).one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    user_id = _parse_user_id(x_user_id)
    _evaluate_pdp(db, user_id, "hydrate_manage_sources", source.workspace_id)

    if payload.name is not None:
        source.name = payload.name
    if payload.config_json is not None:
        source.config_json = json.dumps(payload.config_json)
    if payload.secrets_ref is not None:
        source.secrets_ref = payload.secrets_ref
    if payload.is_enabled is not None:
        source.is_enabled = payload.is_enabled

    db.commit()
    db.refresh(source)
    return WorkspaceSourceOut.model_validate(source)


@router.get("/sources", response_model=List[WorkspaceSourceOut])
def list_sources(workspace_id: str = Query(...), db: Session = Depends(get_db)) -> List[WorkspaceSourceOut]:
    sources = db.query(WorkspaceSource).filter(WorkspaceSource.workspace_id == workspace_id).all()
    return [WorkspaceSourceOut.model_validate(source) for source in sources]


@router.post("/alerts/{alert_id}/acknowledge", response_model=HydrationAlertOut)
def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str = Query("system"),
    db: Session = Depends(get_db),
):
    manager = AlertManager(db)
    alert = manager.acknowledge_alert(alert_id, acknowledged_by)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return HydrationAlertOut.model_validate(alert)


# Demo source seeding constants
DEMO_WORKSPACE_ID = "demo"
DEMO_SOURCE_NAME = "Demo FS"
DEMO_SOURCE_CONFIG = {"root_path": "/app"}


def seed_demo_source(db: Session) -> Optional[WorkspaceSource]:
    """Seed a demo hydration source for the demo workspace. Idempotent."""
    existing = (
        db.query(WorkspaceSource)
        .filter(
            WorkspaceSource.workspace_id == DEMO_WORKSPACE_ID,
            WorkspaceSource.name == DEMO_SOURCE_NAME,
        )
        .first()
    )
    if existing:
        return existing

    source = WorkspaceSource(
        workspace_id=DEMO_WORKSPACE_ID,
        source_type=SourceType.SERVER_FS,
        name=DEMO_SOURCE_NAME,
        config_json=json.dumps(DEMO_SOURCE_CONFIG),
        is_enabled=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.post("/sources/seed-demo", response_model=WorkspaceSourceOut)
def seed_demo_endpoint(db: Session = Depends(get_db)):
    """Seed a demo hydration source for the demo workspace. Idempotent.

    Creates a server_fs source for workspace 'demo' with root_path '/app'.
    If the source already exists, returns the existing source.
    """
    source = seed_demo_source(db)
    return WorkspaceSourceOut.model_validate(source)
