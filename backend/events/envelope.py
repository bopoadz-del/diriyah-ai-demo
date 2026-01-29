"""Event envelope schema for event sourcing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str
    ts: str
    workspace_id: Optional[int]
    actor_id: Optional[int]
    correlation_id: Optional[str]
    source: str
    payload_json: str

    @classmethod
    def build(
        cls,
        event_type: str,
        source: str,
        payload: Dict[str, Any],
        workspace_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        event_id: Optional[str] = None,
        ts: Optional[str] = None,
    ) -> "EventEnvelope":
        return cls(
            event_id=event_id or str(uuid.uuid4()),
            event_type=event_type,
            ts=ts or datetime.now(timezone.utc).isoformat(),
            workspace_id=workspace_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            source=source,
            payload_json=json.dumps(payload),
        )

    def to_fields(self) -> Dict[str, str]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "ts": self.ts,
            "workspace_id": "" if self.workspace_id is None else str(self.workspace_id),
            "actor_id": "" if self.actor_id is None else str(self.actor_id),
            "correlation_id": self.correlation_id or "",
            "source": self.source,
            "payload_json": self.payload_json,
        }

    @classmethod
    def from_fields(cls, fields: Dict[str, Any]) -> "EventEnvelope":
        workspace_raw = fields.get("workspace_id")
        actor_raw = fields.get("actor_id")
        workspace_id = int(workspace_raw) if workspace_raw not in (None, "") else None
        actor_id = int(actor_raw) if actor_raw not in (None, "") else None
        correlation_id = fields.get("correlation_id") or None
        return cls(
            event_id=str(fields.get("event_id")),
            event_type=str(fields.get("event_type")),
            ts=str(fields.get("ts")),
            workspace_id=workspace_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            source=str(fields.get("source")),
            payload_json=str(fields.get("payload_json")),
        )
