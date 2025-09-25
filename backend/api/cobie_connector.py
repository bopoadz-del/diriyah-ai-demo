from fastapi import APIRouter

router = APIRouter()

@router.get("/cobie_connector-ping")
async def ping():
    return {"service": "cobie_connector", "status": "ok"}
