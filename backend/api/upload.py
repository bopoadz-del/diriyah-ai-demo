"""Upload endpoint with Drive stubs for Render deployments."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, File, UploadFile

from backend.services import google_drive, stub_state

router = APIRouter()


def _resolve_project_id(project_id: Optional[str]) -> str:
    if project_id:
        return str(project_id)
    projects = stub_state.list_projects()
    if projects:
        first_project = projects[0]
        resolved = first_project.get("id")
        if resolved is not None:
            return str(resolved)
    return "default"


def _perform_upload(
    project_id: str,
    file: UploadFile,
    *,
    chat_id: Optional[int],
    drive_folder_id: Optional[str],
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


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = None,
    chat_id: Optional[int] = None,
    drive_folder_id: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_project_id = _resolve_project_id(project_id)
    return _perform_upload(
        resolved_project_id,
        file,
        chat_id=chat_id,
        drive_folder_id=drive_folder_id,
    )


@router.post("/upload/{project_id}")
async def upload_file_for_project(
    project_id: str,
    file: UploadFile = File(...),
    chat_id: Optional[int] = None,
    drive_folder_id: Optional[str] = None,
) -> Dict[str, Any]:
    return _perform_upload(
        project_id,
        file,
        chat_id=chat_id,
        drive_folder_id=drive_folder_id,
    )
