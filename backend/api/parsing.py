"""Document parsing endpoints that consume Google Drive files."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.services.drive_service import download_file
from backend.services.extract_text import extract_file_content

router = APIRouter()


@router.get("/parsing/extract")
def extract_document(
    file_id: str = Query(..., description="Google Drive file identifier"),
    extension: str | None = Query(
        default=None,
        description="Optional file extension hint (e.g. .pdf, .docx)",
    ),
) -> dict[str, object]:
    """Extract text content from a Drive-backed document."""

    if not file_id.strip():
        raise HTTPException(status_code=400, detail="file_id is required")

    local_path = download_file(file_id, extension=extension)
    content = extract_file_content(local_path)
    return {"status": "ok", "file_id": file_id, "content": content, "local_path": local_path}


__all__ = ["router"]
