from fastapi import APIRouter, UploadFile, File, Depends, Query
import shutil, os
from sqlalchemy.orm import Session
from ..services.extract_service import extract_text
from ..services.rag_service import add_document
from ..services.drive_service import upload_file_to_project
from ..db import get_db
from .. import models
from openai import OpenAI
import os as _os

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

client = OpenAI(api_key=_os.getenv("OPENAI_API_KEY")) if _os.getenv("OPENAI_API_KEY") else None

@router.post("/upload/{project_id}")
async def upload_doc(
    project_id: int,
    file: UploadFile = File(...),
    chat_id: int | None = Query(default=None),
    drive_folder_id: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    # Save local
    local_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(local_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Upload to Drive if requested
    if drive_folder_id:
        with open(local_path, "rb") as f:
            data = f.read()
        upload_file_to_project(drive_folder_id, data, file.filename, file.content_type or "application/octet-stream")

    # Extract + index
    text = extract_text(local_path)
    add_document(str(project_id), text, file.filename)

    summary = None
    if client:
        try:
            prompt = f"Summarize this file in 5–8 bullets with key risks/actions:\n\n{text[:8000]}"
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0.2
            )
            summary = resp.choices[0].message.content.strip()
        except Exception:
            summary = "(auto-summary unavailable)"

    if chat_id and summary:
        msg = models.Message(chat_id=chat_id, role="assistant", content=f"**Auto-summary of {file.filename}:**\n\n{summary}")
        db.add(msg); db.commit()

    return {"status": "ok", "indexed_bytes": len(text.encode('utf-8')), "summarized": bool(summary)}