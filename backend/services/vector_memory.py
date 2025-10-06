"""Utilities for tracking the project currently targeted by chat sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

_UNSET = object()


@dataclass(frozen=True)
class ActiveProject:
    """Lightweight representation of the active project context."""

    id: Any | None = None
    collection: Any | None = None


_active_project: ActiveProject | None = None


def _coerce_to_active_project(
    project: ActiveProject | Mapping[str, Any] | Any,
    *,
    project_id: Optional[Any] = None,
    collection: Any = _UNSET,
) -> ActiveProject:
    """Normalize different project representations into an :class:`ActiveProject`."""

    if isinstance(project, ActiveProject):
        id_value = project.id
        collection_value = project.collection
    elif isinstance(project, Mapping):
        id_value = project.get("id")
        collection_value = project.get("collection")
    elif project is None:
        id_value = None
        collection_value = None
    else:
        id_value = project
        collection_value = None

    if project_id is not None:
        id_value = project_id

    if collection is not _UNSET:
        collection_value = collection

    return ActiveProject(id=id_value, collection=collection_value)


def set_active_project(
    project: ActiveProject | Mapping[str, Any] | Any = None,
    *,
    project_id: Optional[Any] = None,
    collection: Any = _UNSET,
) -> None:
    """Persist the active project payload used by chat interactions."""

    global _active_project

    if project is None and project_id is None and collection is _UNSET:
        _active_project = None
        return

    target = project if project is not None else ActiveProject()
    _active_project = _coerce_to_active_project(
        target,
        project_id=project_id,
        collection=collection,
    )


def get_active_project() -> ActiveProject | None:
    """Return information about the active project."""

    return _active_project


__all__ = ["ActiveProject", "get_active_project", "set_active_project"]
