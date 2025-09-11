"""Top‑level extractor functions for converting various document formats into
plain text.  This module exposes a single entry point ``extract_from_bytes``
that dispatches to the appropriate format specific parser based on the
provided MIME type.

Supported formats include:
    * PDF (application/pdf) – extracted with ``pypdf``.
    * Word (application/vnd.openxmlformats-officedocument.wordprocessingml.document,
      application/msword) – extracted with ``python‑docx``.
    * Excel (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
      – extracted with ``openpyxl`` by concatenating all sheet cell values.
    * CSV (text/csv) – decoded as UTF‑8 and returned directly.
    * Plain text (text/plain) – returned directly.

If the MIME type is not recognised, the extractor attempts to decode the
bytes as UTF‑8.  For any unsupported binary formats it returns an empty
string.
"""

from __future__ import annotations

import csv
import io
from typing import Callable, Dict

from .pdf_extractor import extract_pdf_bytes
from .docx_extractor import extract_docx_bytes
from .excel_extractor import extract_excel_bytes

# Mapping of MIME types to extractor functions
_EXTRACTORS: Dict[str, Callable[[bytes], str]] = {
    "application/pdf": extract_pdf_bytes,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extract_docx_bytes,
    "application/msword": extract_docx_bytes,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": extract_excel_bytes,
    "text/csv": lambda data: data.decode("utf-8", errors="ignore"),
    "text/plain": lambda data: data.decode("utf-8", errors="ignore"),
}


def extract_from_bytes(mime_type: str, data: bytes) -> str:
    """Return plain text extracted from ``data`` based on ``mime_type``.

    This function looks up the appropriate format specific extractor.  If
    no extractor is registered for the given MIME type, it falls back to
    decoding the bytes as UTF‑8.  Binary formats that cannot be decoded
    return an empty string.

    Args:
        mime_type: The MIME type string reported by Google Drive.
        data: Raw bytes of the file content.

    Returns:
        Extracted plain text or an empty string if extraction failed.
    """
    extractor = _EXTRACTORS.get(mime_type)
    try:
        if extractor:
            return extractor(data) or ""
        # Unknown type – attempt to decode as UTF‑8
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""
