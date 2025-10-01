from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from backend.services import google_drive

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict[str, object]:
    """Upload ``file`` to Drive when available and return debugging metadata."""

    contents = await file.read()
    size = len(contents)
    # Reset the read pointer so the Drive integration can access the payload.
    await file.seek(0)

    drive_file_id = google_drive.upload_to_drive(file)
    stubbed = google_drive.drive_stubbed()

    return {
        "filename": file.filename,
        "size": size,
        "status": "stubbed" if stubbed else "uploaded",
        "drive_file_id": drive_file_id,
        "stubbed": stubbed,
        "error": google_drive.drive_service_error(),
    }
