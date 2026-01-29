"""Minimal event emitter interface for regression hooks."""

from __future__ import annotations

from typing import Callable, Iterable, Optional

from backend.events.envelope import EventEnvelope


class EventEmitter:
    """Simple in-process emitter used for regression hooks."""

    def __init__(self, handlers: Optional[Iterable[Callable[[EventEnvelope], None]]] = None) -> None:
        self._handlers = list(handlers or [])

    def emit(self, event: EventEnvelope) -> None:
        for handler in self._handlers:
            handler(event)

    def register(self, handler: Callable[[EventEnvelope], None]) -> None:
        self._handlers.append(handler)
