"""Event envelope helpers for event sourcing."""

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
    def create(
        cls,
        *,
        event_type: str,
        source: str,
        payload: Dict[str, Any],
        workspace_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
    ) -> "EventEnvelope":
        payload_json = json.dumps(payload)
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            ts=datetime.now(timezone.utc).isoformat(),
            workspace_id=workspace_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            source=source,
            payload_json=payload_json,
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
        def _value(key: str) -> str:
            value = fields.get(key, "")
            if isinstance(value, bytes):
                return value.decode()
            return str(value)

        workspace_id_value = _value("workspace_id")
        actor_id_value = _value("actor_id")
        return cls(
            event_id=_value("event_id"),
            event_type=_value("event_type"),
            ts=_value("ts"),
            workspace_id=int(workspace_id_value) if workspace_id_value else None,
            actor_id=int(actor_id_value) if actor_id_value else None,
            correlation_id=_value("correlation_id") or None,
            source=_value("source"),
            payload_json=_value("payload_json"),
        )
