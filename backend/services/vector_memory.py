 codex/update-active-project-storage-structure
from typing import Any, Dict, Optional


_active_project: Optional[Dict[str, Any]] = None


def set_active_project(project: Optional[Dict[str, Any]]):
    """Persist the currently active project.

    The active project is stored as a dictionary so that both the project
    identifier and any associated collection-like object can be retrieved by
    other services. Passing ``None`` clears the active project.

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
 main
    """

    global _active_project

codex/update-active-project-storage-structure
    if project is None:
        _active_project = None
        return

    if isinstance(project, str):
        _active_project = {"id": project, "collection": None}
        return

    if not isinstance(project, dict):
        raise TypeError("project must be a mapping with 'id' and 'collection' keys")

    _active_project = {
        "id": project.get("id"),
        "collection": project.get("collection"),
    }


def get_active_project() -> Optional[Dict[str, Any]]:
    """Return the currently active project structure, if any."""

    return _active_project

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
 main
