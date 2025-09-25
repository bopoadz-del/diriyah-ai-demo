from fastapi import APIRouter

router = APIRouter()

@router.get("/bcf_connector-ping")
async def ping():
    return {"service": "bcf_connector", "status": "ok"}
