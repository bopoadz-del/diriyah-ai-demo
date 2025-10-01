from typing import Any, Dict, Optional


_active_project: Optional[Dict[str, Any]] = None


def set_active_project(project: Optional[Dict[str, Any]]):
    """Persist the currently active project.

    The active project is stored as a dictionary so that both the project
    identifier and any associated collection-like object can be retrieved by
    other services. Passing ``None`` clears the active project.
    """

    global _active_project

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
