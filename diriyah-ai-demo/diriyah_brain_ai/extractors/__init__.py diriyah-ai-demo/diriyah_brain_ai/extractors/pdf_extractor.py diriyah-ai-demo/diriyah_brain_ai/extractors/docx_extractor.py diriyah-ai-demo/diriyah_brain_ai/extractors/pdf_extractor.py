"""PDF extraction utilities.

This module uses the ``pypdf`` library to extract text from PDF files.
The extraction operates on in‑memory byte data to avoid writing
temporary files to disk.  If extraction fails, an empty string is
returned.
"""

from __future__ import annotations

import io
from typing import Optional

# The pypdf library is optional.  It is imported lazily inside the
# extraction function to allow the module to be imported even if
# pypdf is not installed in the environment.  If pypdf is missing,
# the extractor will return an empty string rather than raising.


def extract_pdf_bytes(data: bytes) -> str:
    """Extract plain text from a PDF represented by raw bytes.

    The function attempts to import ``pypdf.PdfReader`` and will
    gracefully handle the absence of the dependency by returning an
    empty string.  If a PDF is successfully parsed, all page text is
    concatenated with newlines.

    Args:
        data: Raw PDF data.

    Returns:
        A single string containing the concatenated text of all pages.
        If the PDF cannot be read or the library is missing, returns
        an empty string.
    """
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(pages)
    except Exception:
        return ""
