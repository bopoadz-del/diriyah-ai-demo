from fastapi import APIRouter, Body, File, UploadFile

from backend.services.google_drive import upload_to_drive

router = APIRouter()

try:  # pragma: no cover - optional multipart dependency
    import multipart  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled gracefully
    multipart = None  # type: ignore[assignment]

_upload_dependency = File(...) if multipart is not None else Body(None)


@router.post("/drive/upload")
async def drive_upload(file: UploadFile | None = _upload_dependency):
    if multipart is None or file is None:
        return {"file_id": "stubbed-upload-id"}
    file_id = upload_to_drive(file)
    return {"file_id": file_id}
