from fastapi import APIRouter
router = APIRouter()
@router.get("/aconex/status")
def aconex_status(): return {"status":"ok","message":"Aconex API not wired yet"}