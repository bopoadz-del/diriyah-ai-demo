from fastapi import APIRouter, File, UploadFile

from backend.services import google_drive

router = APIRouter()


@router.post("/vision")
async def analyze_image(file: UploadFile = File(...)):
    """Analyse an image and optionally store the artefact on Drive."""

    service = google_drive.get_drive_service()
    detections = []
    if service is None:
        return {
            "status": "stubbed",
            "detections": detections,
            "file_id": google_drive.upload_to_drive(file, lookup_service=False),
            "detail": google_drive.drive_service_error(),
        }

    file_id = google_drive.upload_to_drive(file, service=service, lookup_service=False)
    return {
        "status": "ok",
        "detections": detections,
        "file_id": file_id,
    }
