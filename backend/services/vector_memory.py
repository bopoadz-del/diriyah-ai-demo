"""Utilities for tracking the project currently targeted by chat sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Option codex/update-project-handling-in-vector_memory
_UNSET: Any = object(
_DEFAULT_PROJECT: MutableMapping[str, Any] = {"id": None, "collection": None}
_active_project: MutableMapping[str, Any] | None = Non.  main


@dataclass(frozen=True)
class ActiveProject:
    """Lightweight representation of the active project context. codex/update-project-handling-in-vector_memory
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

    id_value: Any | None = None
    collection_value: Any | None | Any = _UNSET

    if isinstance(project, ActiveProject):
        id_value = project.id
        collection_value = project.collection
    elif isinstance(project, Mapping):
        id_value = project.get("id")
        if "collection" in project:
            collection_value = project.get("collection")
    elif project is not None:
        id_value = project

    if project_id is not None:
        id_value = project_id

    if collection is not _UNSET:
        collection_value = collection

    if collection_value is _UNSET:
        collection_value = None

    return ActiveProject(id=id_value, collection=collection_value)
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
         main


def set_active_project(
    project: ActiveProject | Mapping[str, Any] | Any = None,
    *,
    project_id: Optional[Any] = None,
    collection: Any = _UNSET,
) -> None:
    """Persist the active project payload used by chat interactions.

    The stored payload always exposes ``id`` and ``collection`` keys so that
    downstream consumers can depend on a consistent structure. Callers may
    provide the entire mapping or override individual fields via keyword
    arguments. Invoking ``set_active_project()`` with no arguments resets the
    payload to ``{"id": None, "collection": None}``.
    """

    global _active_project

    if project is None and project_id is None and collection is _UNSET:
        _active_project = None
        return
        codex/update-project-handling-in-vector_memory
    _active_project = _coerce_to_active_project(
        project if project is not None else {},
        project_id=project_id,
        collection=collection,
    )
    
     
    normalized = _normalize_project(project)

    if project_id is not None:
        normalized["id"] = project_id

    if collection is not None or "collection" not in normalized:
        normalized["collection"] = collecti main


def get_active_project() -> ActiveProject | None:
    """Return information about the active project."""

    return _active_project
  codex/update-project-handling-in-vector_memory
    if _active_project is None:
        return dict(_DEFAULT_PROJECT)
   main

__all__ = ["ActiveProject", "get_active_project", "set_active_project"]
