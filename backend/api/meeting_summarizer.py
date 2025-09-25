from fastapi import APIRouter

router = APIRouter()

@router.get("/meeting_summarizer-ping")
async def ping():
    return {"service": "meeting_summarizer", "status": "ok"}
