"""In-memory storage for the currently active project."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

_active_project: MutableMapping[str, Any] | None = None


def _normalize_project(project: Any) -> MutableMapping[str, Any]:
    """Normalize different project representations into a mutable mapping."""

    if project is None:
        return {}

    if isinstance(project, Mapping):
        return dict(project)

    # Fallback to treating the project as an identifier only.
    return {"id": project}


def set_active_project(
    project: Optional[Mapping[str, Any]] | Any = None,
    *,
    project_id: Optional[str] = None,
    collection: Any = None,
) -> None:
    """Persist information about the active project.

    The project can be supplied as a mapping containing arbitrary keys or as an
    identifier. Optional keyword arguments can override the ``id`` and
    ``collection`` entries to ensure callers receive a consistent structure.
    """

    global _active_project

    normalized = _normalize_project(project)

    if project_id is not None:
        normalized["id"] = project_id

    if collection is not None:
        normalized["collection"] = collection

    _active_project = normalized


def get_active_project() -> MutableMapping[str, Any]:
    """Return information about the active project as a mapping."""

    if _active_project is None:
        return {}

    return _normalize_project(_active_project)
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
"""In-memory storage for the currently active project."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional


_active_project: MutableMapping[str, Any] | None = None


def _normalize_project(project: Any) -> MutableMapping[str, Any]:
    """Normalize different project representations into a mutable mapping."""

    if project is None:
        return {}

    if isinstance(project, Mapping):
        return dict(project)

    # Fallback to treating the project as an identifier only.
    return {"id": project}


def set_active_project(
    project: Optional[Mapping[str, Any]] | Any = None,
    *,
    project_id: Optional[str] = None,
    collection: Any = None,
) -> None:
    """Persist information about the active project.

    The project can be supplied as a mapping containing arbitrary keys or as an
    identifier. Optional keyword arguments can override the ``id`` and
    ``collection`` entries to ensure callers receive a consistent structure.
    """

    global _active_project

    normalized = _normalize_project(project)

    if project_id is not None:
        normalized["id"] = project_id

    if collection is not None:
        normalized["collection"] = collection

    _active_project = normalized


def get_active_project() -> MutableMapping[str, Any]:
    """Return information about the active project as a mapping."""

    if _active_project is None:
        return {}

    return _normalize_project(_active_project)
