"""Tests ensuring vector memory tracks structured active project data."""

from backend.services.vector_memory import (
    ActiveProject,
    get_active_project,
    set_active_project,
)


def teardown_function() -> None:
    """Reset the active project between tests."""

    set_active_project(None)


def test_set_active_project_from_mapping() -> None:
    """Mapping inputs should become :class:`ActiveProject` instances."""

    set_active_project({"id": "proj-1"})

    active = get_active_project()
    assert isinstance(active, ActiveProject)
    assert active.id == "proj-1"
    assert active.collection is None


def test_override_project_details() -> None:
    """Keyword arguments override the provided project information."""

    set_active_project({"id": "proj-2", "collection": "ignored"}, project_id="final", collection="kept")

    active = get_active_project()
    assert isinstance(active, ActiveProject)
    assert active.id == "final"
    assert active.collection == "kept"


def test_clear_active_project() -> None:
    """Passing ``None`` clears the stored active project."""

    set_active_project({"id": "proj-3"})
    set_active_project(None)

    assert get_active_project() is None
