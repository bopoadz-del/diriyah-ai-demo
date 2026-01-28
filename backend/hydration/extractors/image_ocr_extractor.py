"""Image OCR extraction utilities."""

from __future__ import annotations

from typing import Dict, Tuple


def extract_image_text(data: bytes, ocr_enabled: bool = False) -> Tuple[str, Dict]:
    meta: Dict[str, object] = {}
    if not ocr_enabled:
        return "", {"ocr_disabled": True}

    try:
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore
        import io
        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image).strip()
        meta["ocr_used"] = True
        return text, meta
    except Exception as exc:
        meta["error"] = str(exc)
        return "", meta
