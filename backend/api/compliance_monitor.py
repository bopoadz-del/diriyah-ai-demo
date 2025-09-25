from fastapi import APIRouter

router = APIRouter()

@router.get("/compliance_monitor-ping")
async def ping():
    return {"service": "compliance_monitor", "status": "ok"}
