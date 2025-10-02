"""Utilities for tracking the project currently targeted by chat sessions."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

_DEFAULT_PROJECT: MutableMapping[str, Any] = {"id": None, "collection": None}
_active_project: MutableMapping[str, Any] | None = None


def _normalize_project(project: Any) -> MutableMapping[str, Any]:
    """Normalize different project representations into a mutable mapping."""

    if project is None:
        base: MutableMapping[str, Any] = {}
    elif isinstance(project, Mapping):
        base = dict(project)
    else:
        base = {"id": project}

    normalized = dict(_DEFAULT_PROJECT)
    normalized.update(base)
    normalized.setdefault("id", None)
    normalized.setdefault("collection", None)
    return normalized


def set_active_project(
    project: Optional[Mapping[str, Any]] | Any = None,
    *,
    project_id: Optional[str] = None,
    collection: Any = None,
) -> None:
    """Persist the active project payload used by chat interactions.

    The stored payload always exposes ``id`` and ``collection`` keys so that
    downstream consumers can depend on a consistent structure. Callers may
    provide the entire mapping or override individual fields via keyword
    arguments. Invoking ``set_active_project()`` with no arguments resets the
    payload to ``{"id": None, "collection": None}``.
    """

    global _active_project

    if project is None and project_id is None and collection is None:
        _active_project = None
        return

    normalized = _normalize_project(project)

    if project_id is not None:
        normalized["id"] = project_id

    if collection is not None or "collection" not in normalized:
        normalized["collection"] = collection

    _active_project = normalized


def get_active_project() -> MutableMapping[str, Any]:
    """Return information about the active project as a mapping."""

    if _active_project is None:
        return dict(_DEFAULT_PROJECT)

    return _normalize_project(_active_project)
