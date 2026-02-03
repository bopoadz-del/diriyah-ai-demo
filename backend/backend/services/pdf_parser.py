"""
PDF file analysis for Diriyah AI.

This module uses PyMuPDF (imported as ``fitz``) to inspect PDF
documents. It returns the number of pages and can generate a
base64‑encoded PNG thumbnail of the first page. If the file cannot
be opened or processed, an exception is raised. In a full
implementation this could be extended to extract drawings, text
layers or perform OCR.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Dict, Any

import fitz  # PyMuPDF


def parse_pdf_file(file_path: Path) -> Dict[str, Any]:
    """
    Inspect a PDF document and return basic metadata and a thumbnail.

    Args:
        file_path: Path to the PDF file.

    Returns:
        A dictionary with ``file_name``, ``file_size``, ``page_count``,
        ``thumbnail_b64`` (or ``None``) and ``message``.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If the file cannot be opened as a PDF.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    file_name = file_path.name
    file_size = file_path.stat().st_size

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF: {exc}")

    page_count = doc.page_count
    thumbnail_b64: str | None = None
    message = "PDF processed successfully."

    if page_count > 0:
        try:
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
            png_bytes = pix.tobytes("png")
            thumbnail_b64 = base64.b64encode(png_bytes).decode("ascii")
        except Exception:
            message = "PDF processed but thumbnail generation failed."
            thumbnail_b64 = None
    doc.close()

    return {
        "file_name": file_name,
        "file_size": file_size,
        "page_count": page_count,
        "thumbnail_b64": thumbnail_b64,
        "message": message,
    }