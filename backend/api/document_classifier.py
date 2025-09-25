from fastapi import APIRouter

router = APIRouter()

@router.get("/document_classifier-ping")
async def ping():
    return {"service": "document_classifier", "status": "ok"}
