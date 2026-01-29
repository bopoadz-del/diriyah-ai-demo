"""Lightweight event envelope used by regression hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class EventEnvelope:
    """Represents an emitted event with payload metadata."""

    event_type: str
    payload: Dict[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: Optional[str] = None
