"""Slack alert helpers."""
from __future__ import annotations
import os
from typing import Dict
import requests

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_alert(message: str, *, level: str = "info") -> Dict[str, str]:
    """Send ``message`` to Slack if the webhook is configured."""
    if not SLACK_WEBHOOK_URL:
        return {
            "status": "skipped",
            "reason": "SLACK_WEBHOOK_URL not set",
            "message": message,
            "level": level,
        }
    response = requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=5)
    if response.status_code == 200:
        return {"status": "sent", "message": message, "level": level}
    return {
        "status": "error",
        "code": str(response.status_code),
        "message": message,
        "level": level,
    }
