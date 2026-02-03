"""
FastAPI endpoints for audio transcription in Diriyah AI.

This module exposes a simple POST endpoint to upload an audio file
and receive basic metadata along with a placeholder transcript. In
future iterations this endpoint can be extended to call real
speech‑to‑text services.
"""

from pathlib import Path
import os
from fastapi import APIRouter, UploadFile, File, HTTPException

from ..services.audio_transcription import transcribe_audio_file
from .upload import UPLOAD_DIR


router = APIRouter()
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/audio/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict:
    """Transcribe an uploaded audio file and return a dummy transcript.

    The file is saved to the ``UPLOAD_DIR`` directory before being
    passed to the transcription service. Only basic WAV metadata is
    extracted in this version.

    Args:
        file: The uploaded audio file.

    Returns:
        A dictionary containing file metadata and a placeholder
        transcript.

    Raises:
        HTTPException: If saving or processing fails.
    """
    try:
        file_path = Path(UPLOAD_DIR) / file.filename
        with open(file_path, "wb") as out_file:
            out_file.write(await file.read())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save audio file: {exc}")

    try:
        result = transcribe_audio_file(file_path)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))