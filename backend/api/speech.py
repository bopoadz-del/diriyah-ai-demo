from fastapi import APIRouter, File, UploadFile

from backend.services import google_drive

router = APIRouter()


@router.post("/speech")
async def speech_to_text(file: UploadFile = File(...)):
    """Transcribe audio and upload artefacts when Drive is available."""

    service = google_drive.get_drive_service()
    if service is None:
        return {
            "status": "stubbed",
            "text": "transcribed text (stub)",
            "file_id": google_drive.upload_to_drive(file, lookup_service=False),
            "detail": google_drive.drive_service_error(),
        }

    file_id = google_drive.upload_to_drive(file, service=service, lookup_service=False)
    return {
        "status": "ok",
        "text": "transcribed text (demo)",
        "file_id": file_id,
    }
