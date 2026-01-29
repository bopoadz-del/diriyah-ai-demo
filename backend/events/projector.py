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
        *,
        stream: str,
        stream_entry_id: Optional[str],
    ) -> bool:
        existing = db.query(EventLog).filter(EventLog.event_id == event.event_id).first()
        if existing:
            return False

        payload = self._payload_dict(event.payload_json)
        log_entry = EventLog(
            event_id=event.event_id,
            stream=stream,
            stream_entry_id=stream_entry_id,
            event_type=event.event_type,
            workspace_id=event.workspace_id,
            actor_id=event.actor_id,
            correlation_id=event.correlation_id,
            payload_json=payload,
        )
        db.add(log_entry)
        self._apply_projection(event, payload, db)
        db.commit()
        return True

    def _apply_projection(self, event: EventEnvelope, payload: dict, db: Session) -> None:
        workspace_id = event.workspace_id
        if workspace_id is None:
            return

        state = db.query(WorkspaceStateProjection).filter_by(workspace_id=workspace_id).one_or_none()
        if not state:
            state = WorkspaceStateProjection(workspace_id=workspace_id)
            db.add(state)

        now = datetime.now(timezone.utc)
        if event.event_type == "hydration.completed":
            state.last_hydration_at = now
            state.last_hydration_job_id = payload.get("job_id")
        elif event.event_type == "learning.dataset.exported":
            state.last_learning_export_at = now
        elif event.event_type == "regression.promoted":
            state.last_promotion_at = now
        state.updated_at = now

    @staticmethod
    def _payload_dict(payload_json: str) -> dict:
        if not payload_json:
            return {}
        try:
            return json.loads(payload_json)
        except json.JSONDecodeError:
            return {}
