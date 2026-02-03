"""
FastAPI endpoint for PDF drawing analysis in Diriyah AI.

This module defines a POST endpoint that accepts a PDF document,
stores it and returns basic metadata such as page count and a
thumbnail of the first page encoded in base64. If the document
cannot be processed, an error is returned.
"""

from pathlib import Path
import os
from fastapi import APIRouter, UploadFile, File, HTTPException

from ..services.pdf_parser import parse_pdf_file
from .upload import UPLOAD_DIR


router = APIRouter()
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/pdf/analyze")
async def analyze_pdf(file: UploadFile = File(...)) -> dict:
    """Analyze an uploaded PDF and return metadata and thumbnail.

    Args:
        file: The uploaded PDF document.

    Returns:
        A dictionary containing file metadata and a base64 thumbnail.

    Raises:
        HTTPException: If saving or processing fails.
    """
    try:
        file_path = Path(UPLOAD_DIR) / file.filename
        with open(file_path, "wb") as out_file:
            out_file.write(await file.read())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save PDF: {exc}")

    try:
        result = parse_pdf_file(file_path)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))