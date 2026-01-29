"""Event envelope structure for Redis Streams event sourcing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class EventEnvelope:
    """Represents an emitted event with metadata and payload."""

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
        payload: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> "EventEnvelope":
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            ts=datetime.now(timezone.utc).isoformat(),
            workspace_id=workspace_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            source=source or "unknown",
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
        )

    def to_fields(self) -> Dict[str, str]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "ts": self.ts,
            "workspace_id": str(self.workspace_id) if self.workspace_id is not None else "",
            "actor_id": str(self.actor_id) if self.actor_id is not None else "",
            "correlation_id": self.correlation_id or "",
            "source": self.source,
            "payload_json": self.payload_json,
        }
