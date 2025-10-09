import hashlib
import hmac
import json
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from urllib.parse import parse_qs

from backend.db import log_alert, log_approval

try:  # pragma: no cover - optional dependency for Render debugging
    import requests  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully
    class _RequestsStub:
        def post(self, *_args, **_kwargs):  # pragma: no cover - tests monkeypatch
            return _StubResponse()

        def __getattr__(self, _item: str):  # pragma: no cover - minimal compatibility
            raise RuntimeError("requests package not installed")

    class _StubResponse:
        status_code = 200

        def raise_for_status(self) -> None:  # pragma: no cover - simple stub
            return None

    requests = _RequestsStub()  # type: ignore[assignment]

try:  # pragma: no cover - optional multipart parsing dependency
    import multipart  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled gracefully
    multipart = None  # type: ignore[assignment]

app = FastAPI()

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
APPROVAL_FILE = Path("/tmp/approvals.json")
REQUIRED_APPROVALS = int(os.getenv("REQUIRED_APPROVALS", "2"))


def load_approvals():
    if APPROVAL_FILE.exists():
        return json.loads(APPROVAL_FILE.read_text())
    return {}


def save_approvals(data):
    APPROVAL_FILE.write_text(json.dumps(data))


def post_thread_update(channel: str, thread_ts: str, text: str):
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={"channel": channel, "thread_ts": thread_ts, "text": text},
    )


def trigger_github_workflow(commit_sha: str, approved: bool, approvers: list[str]):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/deploy-prod.yml/dispatches"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    data = {"ref": "main", "inputs": {"commit_sha": commit_sha}}
    if approved:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()


@app.post("/slack/interactivity")
async def slack_interactivity(request: Request, x_slack_signature: str = Header(None), x_slack_request_timestamp: str = Header(None)):
    body = await request.body()
    sig_basestring = f"v0:{x_slack_request_timestamp}:{body.decode()}"
    my_signature = "v0=" + hmac.new(SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(my_signature, x_slack_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    if multipart is None:
        body_text = (await request.body()).decode()
        parsed = parse_qs(body_text)
        payload_values = parsed.get("payload", ["{}"])
        payload_text = payload_values[0]
    else:
        form = await request.form()
        payload_text = form.get("payload", "{}")
    action_payload = json.loads(payload_text)

    user = action_payload["user"]["name"]
    action = action_payload["actions"][0]["value"]
    commit_sha = action.split("_")[-1]
    response_url = action_payload["response_url"]
    channel = action_payload["channel"]["id"]
    thread_ts = action_payload["message"]["ts"]

    approvals = load_approvals()
    approvals.setdefault(commit_sha, {"approved": [], "rejected": []})

    if action.startswith("approve"):
        if user not in approvals[commit_sha]["approved"]:
            approvals[commit_sha]["approved"].append(user)
            log_approval(commit_sha, user, "approved")
            log_alert(0, "deployment", f"Commit {commit_sha} approved by {user}")
        post_thread_update(channel, thread_ts, f"✅ {user} approved")
    else:
        if user not in approvals[commit_sha]["rejected"]:
            approvals[commit_sha]["rejected"].append(user)
            log_approval(commit_sha, user, "rejected")
            log_alert(0, "deployment", f"Commit {commit_sha} rejected by {user}")
        post_thread_update(channel, thread_ts, f"❌ {user} rejected")

    save_approvals(approvals)

    if len(approvals[commit_sha]["approved"]) >= REQUIRED_APPROVALS:
        final_text = f"✅ Deployment APPROVED ({REQUIRED_APPROVALS}/{REQUIRED_APPROVALS}) by {', '.join(approvals[commit_sha]['approved'])}"
        requests.post(response_url, json={"replace_original": True, "text": final_text})
        trigger_github_workflow(commit_sha, approved=True, approvers=approvals[commit_sha]["approved"])
    elif approvals[commit_sha]["rejected"]:
        final_text = f"❌ Deployment REJECTED by {', '.join(approvals[commit_sha]['rejected'])}"
        requests.post(response_url, json={"replace_original": True, "text": final_text})
    else:
        requests.post(response_url, json={"replace_original": False, "text": "Pending approvals"})

    return {"ok": True}
