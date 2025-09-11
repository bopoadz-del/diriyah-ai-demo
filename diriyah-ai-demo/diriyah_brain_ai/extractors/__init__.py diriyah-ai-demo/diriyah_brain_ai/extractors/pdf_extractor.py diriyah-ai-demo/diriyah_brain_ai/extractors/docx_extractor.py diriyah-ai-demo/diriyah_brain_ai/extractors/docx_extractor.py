"""DOCX extraction utilities.

This module extracts text from Microsoft Word documents in ``.docx``
format using the ``python‑docx`` library.  It operates on bytes held
in memory and returns a plain text representation of the document.
"""

from __future__ import annotations

import io
from typing import Optional

# The python-docx library is optional.  It is imported lazily inside
# the extraction function.  If unavailable, the extractor falls back
# to UTF‑8 decode and returns the raw text if possible.


def extract_docx_bytes(data: bytes) -> str:
    """Extract plain text from a DOCX represented by raw bytes.

    Args:
        data: Raw DOCX data.

    Returns:
        Concatenated paragraph text from the document, or if
        ``python-docx`` is not installed, attempts to decode the
        content as UTF‑8.  In case of any failure, returns an empty
        string.
    """
    try:
        from docx import Document  # type: ignore
    except Exception:
        # If python-docx is not available, attempt to decode the raw
        # bytes as text directly.  Most docx files are ZIP archives so
        # this will not produce useful content, but it avoids raising.
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    try:
        buf = io.BytesIO(data)
        doc = Document(buf)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    except Exception:
        return ""
