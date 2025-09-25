from fastapi import APIRouter

router = APIRouter()

@router.get("/knowledge_graph-ping")
async def ping():
    return {"service": "knowledge_graph", "status": "ok"}
