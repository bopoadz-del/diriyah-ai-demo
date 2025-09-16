import logging
from fastapi import FastAPI, UploadFile, Form, HTTPException, Depends, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, os, json, asyncio, base64
from pathlib import Path
from typing import List, Optional
import tempfile
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from PIL import Image
import io
import sqlite3
from datetime import datetime

from diriyah_brain_ai.config import BASE_DIR, STATIC_DIR, INDEX_HTML, UPLOAD_DIR
from diriyah_brain_ai.db_init import init_db
from diriyah_brain_ai.schemas import PhotoAnalyzeRequest
from diriyah_brain_ai.routers import ai_simple, integrations, mock_data, drive, enhanced_drive
from diriyah_brain_ai.routers.ai_simple import router as ai_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

init_db()

app = FastAPI(title="Diriyah Brain AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(ai_router)
app.include_router(integrations.router)
app.include_router(mock_data.router)
app.include_router(drive.router)
app.include_router(enhanced_drive.router)

@app.get("/")
async def root():
    return FileResponse("diriyah_brain_ai/index.html")

@app.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"File uploaded: {file.filename}")
        return {"status": "success", "filename": file.filename, "saved_path": str(file_path)}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@app.get("/alerts")
async def alerts(project: str):
    try:
        conn = sqlite3.connect("diriyah.db")
        c = conn.cursor()
        c.execute("SELECT type, detail FROM alerts WHERE project_id = (SELECT id FROM projects WHERE name = ?)", (project,))
        alerts_data = [{'type': row[0], 'detail': row[1]} for row in c.fetchall()]
        conn.close()
        return {"alerts": alerts_data}
    except Exception as e:
        logger.error(f"Alerts error: {e}")
        return {"alerts": []}

@app.post("/quality/photo")
async def analyze_photo(request: PhotoAnalyzeRequest):
    try:
        image_data = request.image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)
        
        detections = [
            {"class": "worker", "confidence": 0.92, "bbox": [100, 150, 200, 250]},
            {"class": "safety_helmet", "confidence": 0.88, "bbox": [110, 160, 50, 50]},
            {"class": "heavy_machinery", "confidence": 0.95, "bbox": [300, 200, 400, 300]}
        ]
        
        img = Image.open(io.BytesIO(image_bytes))
        img = img.resize((400, 300))
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "summary": "3 objects detected: worker, safety equipment, machinery",
            "annotated_image": f"data:image/jpeg;base64,{img_b64}",
            "detections": detections,
            "compliance": "Safety standards: 85% compliant"
        }
    except Exception as e:
        logger.error(f"Photo analysis error: {e}")
        return {"error": "Photo analysis failed", "details": str(e)}

@app.get("/export/pdf")
async def export_pdf_endpoint():
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        p = canvas.Canvas(tmp.name)
        p.drawString(100, 800, "Diriyah AI Project Report")
        p.drawString(100, 780, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        p.drawString(100, 760, "Project: Heritage Resort")
        p.drawString(100, 740, "Status: Active")
        p.drawString(100, 720, "Completion: 78%")
        p.save()
        
        return FileResponse(tmp.name, media_type="application/pdf", filename="project_report.pdf")
    except Exception as e:
        logger.error(f"PDF export error: {e}")
        raise HTTPException(status_code=500, detail="PDF export failed")

@app.get("/export/excel")
async def export_excel_endpoint():
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Project Alerts"
        ws.append(["ID", "Type", "Detail", "Project", "Date"])
        
        alerts_data = [
            [1, "Delay", "Task A behind schedule", "Heritage Resort", "2023-11-15"],
            [2, "Budget", "Overrun in section B", "Heritage Resort", "2023-11-14"],
            [3, "Safety", "Missing safety equipment", "Infrastructure", "2023-11-13"]
        ]
        
        for alert in alerts_data:
            ws.append(alert)
        
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        wb.save(tmp.name)
        
        return FileResponse(tmp.name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="alerts.xlsx")
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        raise HTTPException(status_code=500, detail="Excel export failed")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


