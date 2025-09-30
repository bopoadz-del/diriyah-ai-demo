import os
from fastapi import APIRouter, HTTPException

from backend.services import google_drive

USE_FIXTURE_PROJECTS = os.getenv("USE_FIXTURE_PROJECTS", "true").lower() == "true"

PROJECT_FIXTURES = {
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

router = APIRouter()

@router.get("/projects")
def list_projects():
    if USE_FIXTURE_PROJECTS:
        return {"status": "stubbed", "projects": list(PROJECT_FIXTURES.values())}

    service = google_drive.get_drive_service()
    if service is None:
        return {
            "status": "stubbed",
            "projects": google_drive.list_project_folders(lookup_service=False),
            "detail": google_drive.drive_service_error(),
        }

    return {
        "status": "ok",
        "projects": google_drive.list_project_folders(
            service=service, lookup_service=False
        ),
    }


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    if USE_FIXTURE_PROJECTS:
        project = PROJECT_FIXTURES.get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"status": "stubbed", "project": project}

    service = google_drive.get_drive_service()
    if service is None:
        return {
            "status": "stubbed",
            "project": google_drive.get_project(project_id),
            "detail": google_drive.drive_service_error(),
        }

    return {"status": "ok", "project": google_drive.get_project(project_id)}

@router.post("/projects/{project_id}/context")
def set_project_context(project_id: str):
    from backend.services import vector_memory
    vector_memory.set_active_project(project_id)
    return {"status": "context_set", "project_id": project_id}
