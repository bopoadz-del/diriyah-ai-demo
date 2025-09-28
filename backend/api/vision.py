from fastapi import APIRouter, UploadFile, File
from backend.services.google_drive import upload_to_drive
from backend.services.yolo_detector import run_yolo
router = APIRouter()
@router.post("/vision")
async def upload_image(image: UploadFile = File(...)):
    file_id = upload_to_drive(image)
    detections = run_yolo(file_id)
    return {"file_id": file_id, "detections": detections}
