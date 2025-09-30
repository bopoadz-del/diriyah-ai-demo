from fastapi import APIRouter, File, UploadFile

from backend.services import google_drive

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to Drive or return a stubbed identifier."""

    service = google_drive.get_drive_service()
    if service is None:
        return {
            "status": "stubbed",
            "file_id": google_drive.upload_to_drive(file, lookup_service=False),
            "filename": file.filename,
            "detail": google_drive.drive_service_error(),
        }

    file_id = google_drive.upload_to_drive(file, service=service, lookup_service=False)
    return {"status": "ok", "file_id": file_id, "filename": file.filename}
