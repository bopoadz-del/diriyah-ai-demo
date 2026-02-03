"""
FastAPI endpoints for schedule analysis in Diriyah AI.

This module defines a POST endpoint that accepts a schedule file,
saves it to the uploads directory and returns parsed tasks along
with critical path metrics. Supported formats include Primavera XER
and Microsoft Project XML/MPP. Unsupported formats return basic
metadata.
"""

from pathlib import Path
import os
from fastapi import APIRouter, UploadFile, File, HTTPException

from ..services.schedule_parser import parse_schedule_file
from .upload import UPLOAD_DIR


router = APIRouter()

# Ensure the uploads directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/schedule/analyze")
async def analyze_schedule(file: UploadFile = File(...)) -> dict:
    """Analyze an uploaded schedule file and return parsed results.

    The uploaded file is stored in the ``UPLOAD_DIR`` directory. The
    parser detects the file type based on extension and produces a
    result containing tasks, task count and schedule metrics.

    Args:
        file: The uploaded schedule file.

    Returns:
        A dictionary with parsed tasks and analysis.

    Raises:
        HTTPException: If file saving or parsing fails.
    """
    try:
        file_path = Path(UPLOAD_DIR) / file.filename
        # Save the uploaded file
        with open(file_path, "wb") as out_file:
            out_file.write(await file.read())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save schedule file: {exc}")

    try:
        result = parse_schedule_file(file_path)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))