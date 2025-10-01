"""Stub speech-to-text endpoints used for local development and tests."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

router = APIRouter()


@router.get("/speech/diagnostics")
def speech_diagnostics() -> dict[str, str]:
    """Return a stubbed response indicating the speech pipeline is mocked."""

    return {"status": "stubbed", "detail": "Speech pipeline not available in tests"}


@router.post("/speech/{project_id}")
async def speech_to_text(project_id: str, file: UploadFile = File(...)) -> dict[str, str]:
    """Echo the uploaded filename to confirm the speech route is wired up."""

    return {"project_id": project_id, "filename": file.filename or ""}

