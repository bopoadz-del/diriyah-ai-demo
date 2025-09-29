"""Alert-related API routes used by the demo frontend."""
from typing import List
from fastapi import APIRouter, Body
from pydantic import BaseModel
from backend.services.alerts import send_alert

router = APIRouter()

class AlertMessage(BaseModel):
    """Schema describing an alert shown in the UI."""
    message: str
    level: str = "info"
    status: str = "ok"

class CreateAlertRequest(BaseModel):
    """Body payload accepted by :func:`create_alert`."""
    message: str

@router.post("/alerts", response_model=AlertMessage)
def create_alert(payload: CreateAlertRequest = Body(...)) -> AlertMessage:
    """Forward alert payloads to the Slack webhook integration."""
    result = send_alert(payload.message)
    level = result.get("level", "info")
    status = result.get("status", "ok")
    if status == "error":
        level = "error"
    return AlertMessage(
        message=result.get("message", payload.message),
        level=level,
        status=status,
    )

@router.get("/alerts/recent", response_model=List[AlertMessage])
def recent_alerts() -> List[AlertMessage]:
    """Return a curated list of alerts for the debugging dashboard."""
    return [
        AlertMessage(message="BOQ mismatch detected", level="warning"),
        AlertMessage(message="Structural design approved", level="info"),
        AlertMessage(message="Project Gateway-1 at 72% progress", level="info"),
    ]
