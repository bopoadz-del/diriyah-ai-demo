"""Utilities for tracking the project currently targeted by chat sessions."""

from __future__ import annotations

from typing import Any, Mapping

_DEFAULT_PROJECT_PAYLOAD = {"id": None, "collection": None}
_active_project_payload = dict(_DEFAULT_PROJECT_PAYLOAD)


def set_active_project(project: Mapping[str, Any] | None = None) -> None:
    """Set the in-memory active project payload.

    Parameters
    ----------
    project:
        A mapping describing the project context. The mapping should include an
        ``id`` entry as well as an optional ``collection`` used for semantic
        search. When ``None`` is provided the active project is cleared and the
        default payload with ``None`` values is restored.
    """

    global _active_project_payload

    payload = dict(_DEFAULT_PROJECT_PAYLOAD)
    if project:
        payload["id"] = project.get("id")
        payload["collection"] = project.get("collection")

    _active_project_payload = payload


def get_active_project() -> dict[str, Any]:
    """Return a shallow copy of the active project payload."""

    return dict(_active_project_payload)
