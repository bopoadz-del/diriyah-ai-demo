from fastapi import APIRouter

router = APIRouter()

@router.get("/ifc_parser-ping")
async def ping():
    return {"service": "ifc_parser", "status": "ok"}
