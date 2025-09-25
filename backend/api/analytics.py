from fastapi import APIRouter
router = APIRouter()
@router.get("/analytics/summary")
def analytics_summary(): return {"status":"ok","data":{"risk":"N/A","progress":"N/A"}}