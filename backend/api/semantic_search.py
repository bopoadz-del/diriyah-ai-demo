from fastapi import APIRouter

router = APIRouter()

@router.get("/semantic_search-ping")
async def ping():
    return {"service": "semantic_search", "status": "ok"}
