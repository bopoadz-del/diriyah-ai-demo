from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/vision")
async def analyze_image(file: UploadFile = File(...)):
    # Stub implementation
    return {"detections": []}