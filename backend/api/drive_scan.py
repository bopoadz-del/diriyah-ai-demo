"""Endpoints that surface Google Drive project folders to the UI."""
from typing import Dict, List
from fastapi import APIRouter
from backend.services.google_drive import list_project_folders

router = APIRouter()

_KEYWORDS = ("villa", "tower", "phase", "building")

@router.get("/projects/scan-drive")
def scan_projects() -> Dict[str, List[str]]:
    """Return a de-duplicated list of Drive folders that resemble projects."""
    projects: List[str] = []
    for drive_file in list_project_folders():
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
    return {"projects": deduped}
