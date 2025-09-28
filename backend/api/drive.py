from fastapi import APIRouter, UploadFile, File
from backend.services.google_drive import upload_to_drive
router = APIRouter()
@router.post("/drive/upload")
async def drive_upload(file: UploadFile = File(...)):
    file_id = upload_to_drive(file)
    return {"file_id": file_id}
