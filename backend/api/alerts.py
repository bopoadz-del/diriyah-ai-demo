from fastapi import APIRouter
from backend.services.alerts import send_alert
router = APIRouter()
@router.post("/alerts")
def create_alert(message: str):
    return send_alert(message)
@router.get("/alerts/recent")
def recent_alerts():
    return [
        {"message": "BOQ mismatch detected", "level": "warning"},
        {"message": "Structural design approved", "level": "info"},
        {"message": "Project Gateway-1 at 72% progress", "level": "info"},
    ]
