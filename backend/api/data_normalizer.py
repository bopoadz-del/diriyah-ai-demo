from fastapi import APIRouter

router = APIRouter()

@router.get("/data_normalizer-ping")
async def ping():
    return {"service": "data_normalizer", "status": "ok"}
