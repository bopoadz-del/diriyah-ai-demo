from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

router = APIRouter()


@router.post("/upload")
async def upload_stub(file: UploadFile = File(...)) -> dict[str, object]:
    """Return metadata about an uploaded file without persisting it."""

    content = await file.read()
    size = len(content)
    # Reset the read pointer so other code paths can re-read the file if needed.
    await file.seek(0)
    return {"filename": file.filename, "size": size, "status": "stubbed"}
