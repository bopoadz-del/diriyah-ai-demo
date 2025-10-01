"""Endpoints that surface Google Drive project folders to the UI."""

from typing import Any, Dict, List

from fastapi import APIRouter

from backend.services import google_drive

router = APIRouter()

_KEYWORDS = ("villa", "tower", "phase", "building")

@router.get("/projects/scan-drive")
def scan_projects() -> Dict[str, Any]:
    """Return a de-duplicated list of Drive folders that resemble projects."""
    service = google_drive.get_drive_service()
    if service is None:
        return {
            "status": "stubbed",
            "projects": [],
            "detail": google_drive.drive_service_error(),
            "detail_source": google_drive.drive_service_error_source(),
        }

    projects: List[str] = []
    for drive_file in google_drive.list_project_folders(
        service=service, lookup_service=False
    ):
        name = drive_file.get("name", "")
        if any(keyword in name.lower() for keyword in _KEYWORDS):
            projects.append(name)
    # dedupe preserve order
    seen = set()
    deduped: List[str] = []
    for project in projects:
        if project not in seen:
            deduped.append(project)
            seen.add(project)
    return {"status": "ok", "projects": deduped}
