from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..services.analytics_service import get_logs

router = APIRouter()

@router.get("/analytics")
def analytics(limit: int = 100, db: Session = Depends(get_db)):
    return get_logs(db, limit)