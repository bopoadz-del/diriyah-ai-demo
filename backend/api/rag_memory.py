from fastapi import APIRouter

router = APIRouter()

@router.get("/rag_memory-ping")
async def ping():
    return {"service": "rag_memory", "status": "ok"}
