from fastapi import APIRouter, UploadFile, File
import shutil, os
from ..services.vision_service import analyze_image
from ..services.rag_service import add_document

router = APIRouter()
IMG_DIR = "images"
os.makedirs(IMG_DIR, exist_ok=True)

@router.post("/vision/{project_id}")
async def analyze(project_id: str, file: UploadFile = File(...)):
    path = os.path.join(IMG_DIR, file.filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    detections = analyze_image(path)
    summary = f"Found {len(detections)} objects: " + ", ".join([d['class'] for d in detections])
    add_document(project_id, summary, file.filename)

    return {"detections": detections, "summary": summary}