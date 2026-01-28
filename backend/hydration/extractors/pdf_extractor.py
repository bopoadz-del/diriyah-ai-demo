"""PDF extraction utilities."""

from __future__ import annotations

from typing import Dict, Tuple


def extract_pdf(data: bytes, ocr_enabled: bool = False) -> Tuple[str, Dict]:
    text = ""
    meta: Dict[str, object] = {}

    try:
        from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(data)
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        meta["page_count"] = len(reader.pages)
    except Exception as exc:
        meta["error"] = str(exc)

    if not text and ocr_enabled:
        try:
            import pytesseract  # type: ignore
            from pdf2image import convert_from_bytes  # type: ignore
            images = convert_from_bytes(data)
            ocr_texts = [pytesseract.image_to_string(image) for image in images]
            text = "\n".join(ocr_texts).strip()
            meta["ocr_used"] = True
            meta["ocr_pages"] = len(images)
        except Exception as exc:
            meta["ocr_error"] = str(exc)

    return text, meta
