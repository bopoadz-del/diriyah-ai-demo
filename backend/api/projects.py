from fastapi import APIRouter
from backend.services import google_drive
from backend.services import vector_memory
router = APIRouter()
@router.get("/projects")
def list_projects():
    return google_drive.list_project_folders()
@router.post("/projects/{project_id}/context")
def set_project_context(project_id: str):
    vector_memory.set_active_project(project_id)
    return {"status": "context_set", "project_id": project_id}
