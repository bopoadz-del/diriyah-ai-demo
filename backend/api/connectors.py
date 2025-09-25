from fastapi import APIRouter
router = APIRouter()
@router.get("/connectors/list")
def list_connectors():
    return {"p6":"Not connected","aconex":"Not connected","bim":"Not connected","whatsapp":"Not connected","teams":"Not connected"}