from fastapi import APIRouter, UploadFile, File
from ..services.speech_service import transcribe_audio
from ..services.rag_service import query_rag

router = APIRouter()

@router.post("/speech/{project_id}")
async def speech_to_text(project_id: str, file: UploadFile = File(...)):
    transcript = transcribe_audio(file.file)
    answer = query_rag(project_id, transcript)
    return {"transcript": transcript, "answer": answer}