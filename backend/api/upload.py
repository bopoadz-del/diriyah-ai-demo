from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Stub implementation
    return {"filename": file.filename, "status": "uploaded"}