"""API endpoints for event log access."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.events.models import EventLog

router = APIRouter(prefix="/events", tags=["Events"])


def _serialize_event(event: EventLog) -> dict:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "stream": event.stream,
        "stream_entry_id": event.stream_entry_id,
        "workspace_id": event.workspace_id,
        "actor_id": event.actor_id,
        "correlation_id": event.correlation_id,
        "payload_json": event.payload_json,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("/global")
def list_global_events(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[dict]:
    events = (
        db.query(EventLog)
        .filter(EventLog.stream == "events:global")
        .order_by(EventLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_serialize_event(event) for event in events]


@router.get("/workspace/{workspace_id}")
def list_workspace_events(
    workspace_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[dict]:
    events = (
        db.query(EventLog)
        .filter(EventLog.workspace_id == workspace_id)
        .order_by(EventLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_serialize_event(event) for event in events]
