"""API endpoints for hydration pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
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
    HydrationRunStatus,
    HydrationState,
    HydrationStatus,
    HydrationTrigger,
    WorkspaceSource,
)
from backend.hydration.pipeline import HydrationOptions, HydrationPipeline
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
from backend.redisx.locks import DistributedLock

router = APIRouter(prefix="/hydration", tags=["Hydration"])


def _parse_user_id(x_user_id: Optional[str]) -> int:
    if not x_user_id:
        return 0
    try:
        return int(x_user_id)
    except ValueError:
        return 0


def _evaluate_pdp(db: Session, user_id: int, action: str, workspace_id: str) -> None:
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
):
    user_id = _parse_user_id(x_user_id)
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

    lock = DistributedLock()
    lock_key = f"lock:workspace:{request.workspace_id}:hydration"
    token = lock.acquire(lock_key, ttl=60 * 60 * 2, wait_seconds=0)
    if token is None:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"message": "Hydration already running for workspace."},
        )

    try:
        pipeline = HydrationPipeline(db)
        options = HydrationOptions(
            trigger=HydrationTrigger.API,
            source_ids=request.source_ids,
            force_full_scan=request.force_full_scan,
            max_files=request.max_files,
            dry_run=request.dry_run,
        )
        run = pipeline.hydrate_workspace(request.workspace_id, options)
    finally:
        lock.release(lock_key, token)
    return {"run_id": run.id}


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
