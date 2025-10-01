"""Stub speech-to-text endpoint used for local development and tests."""

from fastapi import APIRouter, File, UploadFile

router = APIRouter()

@router.post("/speech/{project_id}")
async def speech_to_text(project_id: str, file: UploadFile = File(...)) -> dict[str, str]:
    """Echo the uploaded filename to confirm the speech route is wired up."""
    return {"project_id": project_id, "filename": file.filename or ""}
