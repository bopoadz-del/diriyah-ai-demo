from fastapi import APIRouter
from backend.services import cache as cache_service
router = APIRouter()
@router.get("/cache/status")
def cache_status():
    return cache_service.health_check()
