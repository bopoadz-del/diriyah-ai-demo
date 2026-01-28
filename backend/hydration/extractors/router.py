"""Extractor router based on MIME type or file extension."""

from __future__ import annotations

import os
from typing import Callable

from backend.hydration.extractors.docx_extractor import extract_docx
from backend.hydration.extractors.image_ocr_extractor import extract_image_text
from backend.hydration.extractors.pdf_extractor import extract_pdf
from backend.hydration.extractors.xlsx_extractor import extract_xlsx


def get_extractor(filename: str, mime_type: str | None) -> Callable[[bytes, bool], tuple[str, dict]]:
    if mime_type:
        if mime_type == "application/pdf":
            return extract_pdf
        if mime_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            return extract_docx
        if mime_type in (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ):
            return extract_xlsx
        if mime_type.startswith("image/"):
            return extract_image_text

    ext = os.path.splitext(filename or "")[1].lower()
    if ext in {".pdf"}:
        return extract_pdf
    if ext in {".docx", ".doc"}:
        return extract_docx
    if ext in {".xlsx", ".xls"}:
        return extract_xlsx
    if ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
        return extract_image_text

    return extract_docx
