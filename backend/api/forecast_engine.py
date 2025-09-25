from fastapi import APIRouter

router = APIRouter()

@router.get("/forecast_engine-ping")
async def ping():
    return {"service": "forecast_engine", "status": "ok"}
