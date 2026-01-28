"""DOCX extraction utilities."""

from __future__ import annotations

from typing import Dict, Tuple


def extract_docx(data: bytes, ocr_enabled: bool = False) -> Tuple[str, Dict]:
    text = ""
    meta: Dict[str, object] = {}
    try:
        import docx  # type: ignore
        document = docx.Document(io.BytesIO(data))
        paragraphs = [p.text for p in document.paragraphs if p.text]
        text = "\n".join(paragraphs).strip()
        meta["paragraphs"] = len(paragraphs)
    except Exception as exc:
        meta["error"] = str(exc)
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    return text, meta


import io  # noqa: E402
