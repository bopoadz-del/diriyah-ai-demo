from fastapi import APIRouter

router = APIRouter()

@router.get("/action_item_extractor-ping")
async def ping():
    return {"service": "action_item_extractor", "status": "ok"}
