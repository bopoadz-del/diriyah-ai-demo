from fastapi import APIRouter
from backend.services.google_drive import list_project_folders
router = APIRouter()
@router.get("/projects/scan-drive")
def scan_projects():
    files = list_project_folders()
    projects = []
    for f in files:
        name = f["name"]
        if any(k in name.lower() for k in ["villa", "tower", "phase", "building"]):
            projects.append(name)
    return {"projects": list(set(projects))}
