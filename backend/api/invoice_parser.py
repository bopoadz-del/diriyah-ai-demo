from fastapi import APIRouter

router = APIRouter()

@router.get("/invoice_parser-ping")
async def ping():
    return {"service": "invoice_parser", "status": "ok"}
