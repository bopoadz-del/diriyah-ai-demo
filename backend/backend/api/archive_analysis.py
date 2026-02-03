"""
FastAPI endpoint for archive inspection in Diriyah AI.

This module defines a POST endpoint to upload an archive (ZIP, TAR, etc.)
and return a summary of its contents without extracting the files.
"""

from pathlib import Path
import os
from fastapi import APIRouter, UploadFile, File, HTTPException

from ..services.archive_handler import list_archive_contents
from .upload import UPLOAD_DIR


router = APIRouter()
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/archive/analyze")
async def analyze_archive(file: UploadFile = File(...)) -> dict:
    """Inspect an uploaded archive and return its contents summary.

    Args:
        file: The uploaded archive file.

    Returns:
        A dictionary with archive type, file count and entries.

    Raises:
        HTTPException: If saving or reading the archive fails.
    """
    try:
        file_path = Path(UPLOAD_DIR) / file.filename
        with open(file_path, "wb") as out_file:
            out_file.write(await file.read())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save archive: {exc}")

    try:
        result = list_archive_contents(file_path)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))