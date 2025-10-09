from __future__ import annotations

from fastapi import APIRouter, Body, File, HTTPException, UploadFile

router = APIRouter()

try:  # pragma: no cover - optional multipart dependency
    import multipart  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled gracefully
    multipart = None  # type: ignore[assignment]


def _upload_param(*args, **kwargs):
    if multipart is None:
        return Body(None)
    return File(*args, **kwargs)


@router.post("/upload")
async def upload_stub(file: UploadFile | None = _upload_param(...)) -> dict[str, object]:
    """Return metadata about an uploaded file without persisting it."""

    if multipart is None or file is None:
        raise HTTPException(
            status_code=503,
            detail="python-multipart is not installed; uploads are disabled.",
        )

    content = await file.read()
    size = len(content)
    # Reset the read pointer so other code paths can re-read the file if needed.
    await file.seek(0)
    return {"filename": file.filename, "size": size, "status": "stubbed"}
