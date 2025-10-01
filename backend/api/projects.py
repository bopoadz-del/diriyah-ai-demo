"""Project endpoints with stubbed data for Render deployments."""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.services import google_drive, stub_state, vector_memory

USE_FIXTURE_PROJECTS = os.getenv("USE_FIXTURE_PROJECTS", "true").lower() == "true"

PROJECT_FIXTURES: Dict[str, Dict[str, Any]] = {
    "dg-001": {
        "id": "dg-001",
        "name": "Diriyah Gate Cultural District",
        "drive_id": "1DiriyahGateCultural",
        "location": "Diriyah, Riyadh",
        "status": "In Progress",
        "progress_percent": 68,
        "next_milestone": "Q4 2024 infrastructure handover",
        "summary": (
            "Revitalisation of the historic Diriyah area with mixed-use cultural "
            "and hospitality developments."
        ),
    },
    "dg-002": {
        "id": "dg-002",
        "name": "Diriyah Wadi Enhancement",
        "drive_id": "1DiriyahWadiEnhancement",
        "location": "Wadi Hanifah, Diriyah",
        "status": "Design Development",
        "progress_percent": 42,
        "next_milestone": "Landscape design freeze - Feb 2025",
        "summary": (
            "Landscape restoration and public realm upgrades along Wadi Hanifah "
            "to support the greater Diriyah masterplan."
        ),
    },
    "dg-003": {
        "id": "dg-003",
        "name": "Bujairi Terrace Expansion",
        "drive_id": "1BujairiTerraceExpansion",
        "location": "Bujairi, Diriyah",
        "status": "Construction",
        "progress_percent": 81,
        "next_milestone": "Retail fit-out kickoff - May 2024",
        "summary": (
            "Extension of the Bujairi Terrace hospitality destination with new "
            "F&B offerings and public gathering spaces."
        ),
    },
}

stub_state.seed_projects(PROJECT_FIXTURES)

router = APIRouter()


def _serialise_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(project) for project in projects]


@router.get("/projects")
def list_projects() -> Dict[str, Any]:
    """Return either fixture projects or Drive-synchronised ones."""

    if USE_FIXTURE_PROJECTS:
        return {
            "status": "stubbed",
            "projects": _serialise_projects(stub_state.list_projects()),
        }

    service = google_drive.get_drive_service()
    if service is None:
        folders = google_drive.list_project_folders(lookup_service=False)
    else:
        folders = google_drive.list_project_folders(service=service, lookup_service=False)
    projects = [
        stub_state.sync_drive_project(drive_id=folder["id"], name=folder["name"])
        for folder in folders
    ]
    serialised = _serialise_projects(projects)
    if service is None:
        return {
            "status": "stubbed",
            "projects": serialised,
            "detail": google_drive.drive_service_error(),
        }
    return {"status": "ok", "projects": serialised}


@router.get("/projects/sync_drive")
def sync_projects_from_drive() -> list[Dict[str, Any]]:
    """Explicitly trigger a Drive sync and return the latest metadata."""

    service = google_drive.get_drive_service()
    if service is None:
        folders = google_drive.list_project_folders(lookup_service=False)
    else:
        folders = google_drive.list_project_folders(service=service, lookup_service=False)
    projects = [
        stub_state.sync_drive_project(drive_id=folder["id"], name=folder["name"])
        for folder in folders
    ]
    return _serialise_projects(projects)


@router.get("/projects/{project_id}")
def get_project(project_id: str) -> Dict[str, Any]:
    project = stub_state.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if USE_FIXTURE_PROJECTS:
        return {"status": "stubbed", "project": dict(project)}

    service = google_drive.get_drive_service()
    if service is None:
        return {
            "status": "stubbed",
            "project": dict(project),
            "detail": google_drive.drive_service_error(),
        }

    return {"status": "ok", "project": dict(project)}


@router.post("/projects/{project_id}/context")
def set_project_context(project_id: str) -> Dict[str, Any]:
    project = stub_state.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    vector_memory.set_active_project(project_id)
    return {"status": "context_set", "project_id": project_id}
