"""Utilities for tracking the project currently targeted by chat sessions."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

_active_project: MutableMapping[str, Any] | None = None


def _normalize_project(project: Any) -> MutableMapping[str, Any]:
    """Normalize different project representations into a mutable mapping."""

    if isinstance(project, Mapping):
        normalized: MutableMapping[str, Any] = dict(project)
    elif project is None:
        normalized = {}
    else:
        normalized = {"id": project}

    normalized.setdefault("id", None)
    normalized.setdefault("collection", None)

    return normalized


def set_active_project(
    project: Optional[Mapping[str, Any]] | Any = None,
    *,
    project_id: Optional[str] = None,
    collection: Any = None,
) -> None:
    """Persist information about the active project."""

    global _active_project

    if project is None and project_id is None and collection is None:
        _active_project = None
        return

    normalized = _normalize_project(project)

    if project_id is not None:
        normalized["id"] = project_id

    if collection is not None:
        normalized["collection"] = collection

    _active_project = normalized


def get_active_project() -> MutableMapping[str, Any]:
    """Return information about the active project as a mapping."""

    if _active_project is None:
        return _normalize_project(None)

    return _normalize_project(_active_project)
