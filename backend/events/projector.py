"""Event projector for updating DB state from event streams."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Optional

from sqlalchemy.orm import Session

from backend.events.envelope import EventEnvelope
from backend.events.models import EventLog, WorkspaceStateProjection


def _parse_ts(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class EventProjector:
    """Applies events to the database with idempotency."""

    @staticmethod
    def apply(event: EventEnvelope, db: Session) -> bool:
        exists = db.query(EventLog).filter(EventLog.event_id == event.event_id).one_or_none()
        if exists is not None:
            return False

        db.add(
            EventLog(
                event_id=event.event_id,
                event_type=event.event_type,
                ts=event.ts,
                workspace_id=event.workspace_id,
                actor_id=event.actor_id,
                correlation_id=event.correlation_id,
                source=event.source,
                payload_json=event.payload_json,
            )
        )

        payload = {}
        if event.payload_json:
            try:
                payload = json.loads(event.payload_json)
            except json.JSONDecodeError:
                payload = {}

        if event.workspace_id is not None:
            projection = (
                db.query(WorkspaceStateProjection)
                .filter(WorkspaceStateProjection.workspace_id == event.workspace_id)
                .one_or_none()
            )
            if projection is None:
                projection = WorkspaceStateProjection(workspace_id=event.workspace_id)
                db.add(projection)

            timestamp = _parse_ts(event.ts)
            if event.event_type == "hydration.completed":
                projection.last_hydration_at = timestamp or projection.last_hydration_at
                projection.last_hydration_job_id = payload.get("job_id") or projection.last_hydration_job_id
            elif event.event_type == "learning.dataset.exported":
                projection.last_learning_export_at = timestamp or projection.last_learning_export_at
            elif event.event_type == "regression.promoted":
                projection.last_promotion_at = timestamp or projection.last_promotion_at

        db.commit()
        return True
