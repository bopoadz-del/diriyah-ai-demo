"""
FastAPI endpoint for CAD file analysis in Diriyah AI.

This module exposes a POST endpoint that accepts a CAD or 3D model
file, stores it and returns simple metadata including whether it is
recognised as a CAD format. Further analysis could be implemented
using CAD libraries in future iterations.
"""

from pathlib import Path
import os
from fastapi import APIRouter, UploadFile, File, HTTPException

from ..services.cad_parser import parse_cad_file
from .upload import UPLOAD_DIR


router = APIRouter()
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/cad/analyze")
async def analyze_cad(file: UploadFile = File(...)) -> dict:
    """Analyze an uploaded CAD file and return metadata.

    Args:
        file: The uploaded CAD or 3D model file.

    Returns:
        A dictionary describing the file, including whether it is a
        recognised CAD format.

    Raises:
        HTTPException: If saving or processing fails.
    """
    try:
        file_path = Path(UPLOAD_DIR) / file.filename
        with open(file_path, "wb") as out_file:
            out_file.write(await file.read())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save CAD file: {exc}")

    try:
        result = parse_cad_file(file_path)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))