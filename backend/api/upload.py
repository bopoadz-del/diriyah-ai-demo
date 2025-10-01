"""Upload endpoint with Drive stubs for Render deployments."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, File, UploadFile

from backend.services import google_drive, stub_state

router = APIRouter()


@router.post("/upload/{project_id}")
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    chat_id: Optional[int] = None,
    drive_folder_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload a file to Drive or return a stubbed identifier."""

    service = google_drive.get_drive_service()
    if service is None:
        file_id = google_drive.upload_to_drive(file, lookup_service=False)
        status = "stubbed"
        detail = google_drive.drive_service_error()
    else:
        file_id = google_drive.upload_to_drive(file, service=service, lookup_service=False)
        status = "ok"
        detail = None

    stub_state.log_upload(
        project_id=project_id,
        file_name=file.filename or "upload.bin",
        chat_id=chat_id,
        drive_folder_id=drive_folder_id,
    )

    summary = (
        f"Indexed '{file.filename}' for project {project_id}. "
        "Replace this with the output of the real document processing pipeline."
    )
    return {
        "status": status,
        "file_id": file_id,
        "filename": file.filename,
        "summarized": True,
        "summary": summary,
        "detail": detail,
    }
