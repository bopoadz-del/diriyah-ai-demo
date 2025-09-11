"""
whatsapp_adapter.py
-------------------

Stub module for integrating the AI assistant with a WhatsApp work
group.  In a real implementation you would configure the WhatsApp
Business API or Cloud API, subscribe to webhooks and push replies
back to the group.  This stub simply echoes the incoming message.

Endpoint:

POST /whatsapp/webhook

Body:
  JSON payload from WhatsApp webhook

Returns:
  A simple acknowledgement and echo of the last message body
"""

from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    # Extract last message text if present
    text = ""
    try:
        changes = data.get("entry", [])[0].get("changes", [])
        messages = changes[0]["value"].get("messages", []) if changes else []
        text = messages[0].get("text", {}).get("body", "") if messages else ""
    except Exception:
        pass
    return {
        "status": "stub",
        "echo": text
    }