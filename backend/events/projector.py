"""Event projector for workspace state."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Optional

from sqlalchemy.orm import Session

from backend.events.envelope import EventEnvelope
from backend.events.models import EventLog, WorkspaceStateProjection


class EventProjector:
    def apply(
        self,
        event: EventEnvelope,
        db: Session,
        stream: Optional[str] = None,
        stream_entry_id: Optional[str] = None,
    ) -> bool:
        existing = db.query(EventLog).filter(EventLog.event_id == event.event_id).one_or_none()
        if existing:
            return False

        payload = _payload_to_json(event.payload_json)
        event_log = EventLog(
            event_id=event.event_id,
            stream=stream or "events:global",
            stream_entry_id=stream_entry_id,
            event_type=event.event_type,
            workspace_id=event.workspace_id,
            actor_id=event.actor_id,
            correlation_id=event.correlation_id,
            payload_json=payload,
        )
        db.add(event_log)
        self._apply_projection(event, payload, db)
        db.commit()
        return True

    def _apply_projection(self, event: EventEnvelope, payload: dict, db: Session) -> None:
        workspace_id = event.workspace_id
        if workspace_id is None:
            return

        projection = db.query(WorkspaceStateProjection).filter(
            WorkspaceStateProjection.workspace_id == workspace_id
        ).one_or_none()
        if projection is None:
            projection = WorkspaceStateProjection(workspace_id=workspace_id)
            db.add(projection)

        now = datetime.now(timezone.utc)

        if event.event_type == "hydration.completed":
            projection.last_hydration_at = now
            projection.last_hydration_job_id = payload.get("job_id")
            projection.updated_at = now
        elif event.event_type == "learning.dataset.exported":
            projection.last_learning_export_at = now
            projection.updated_at = now
        elif event.event_type == "regression.promoted":
            projection.last_promotion_at = now
            projection.updated_at = now


def _payload_to_json(payload_json: str) -> dict:
    try:
        value = json.loads(payload_json)
        if isinstance(value, dict):
            return value
        return {"value": value}
    except json.JSONDecodeError:
        return {"raw": payload_json}
