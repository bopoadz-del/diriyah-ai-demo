from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/speech")
async def speech_to_text(file: UploadFile = File(...)):
    # Stub implementation
    return {"text": "transcribed text (stub)"}