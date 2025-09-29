from fastapi import APIRouter, UploadFile, File
from ..services.drive_service import list_project_folders, upload_file_to_project

router = APIRouter()

@router.get("/projects/drive")
def get_drive_projects():
    return list_project_folders()

@router.post("/projects/{folder_id}/upload")
async def upload_to_drive(folder_id: str, file: UploadFile = File(...)):
    data = await file.read()
    return upload_file_to_project(folder_id, data, file.filename, file.content_type or "application/octet-stream")