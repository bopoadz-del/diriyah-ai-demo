import os, requests
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
def send_alert(message: str):
    if not SLACK_WEBHOOK_URL:
        return {"status": "skipped", "reason": "SLACK_WEBHOOK_URL not set"}
    resp = requests.post(SLACK_WEBHOOK_URL, json={"text": message})
    return {"status": "sent"} if resp.status_code == 200 else {"status": "error", "code": resp.status_code}
