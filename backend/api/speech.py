from fastapi import APIRouter, UploadFile, File
from backend.services.google_drive import upload_to_drive
from backend.services.speech_to_text import transcribe_audio
router = APIRouter()
@router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    file_id = upload_to_drive(audio)
    text = transcribe_audio(file_id)
    return {"file_id": file_id, "text": text}
