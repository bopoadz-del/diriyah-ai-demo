from fastapi import APIRouter

router = APIRouter()

@router.get("/anomaly_detector-ping")
async def ping():
    return {"service": "anomaly_detector", "status": "ok"}
