import hmac
import hashlib
import importlib
import json
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient


def _signature(secret: str, timestamp: str, body: str) -> str:
    base = f"v0:{timestamp}:{body}"
    digest = hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
    return f"v0={digest}"


@pytest.fixture
def slack_test_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "signing-secret")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("GITHUB_TOKEN", "github-token")
    monkeypatch.setenv("GITHUB_REPO", "example/repo")
    monkeypatch.setenv("REQUIRED_APPROVALS", "1")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")

    module = importlib.import_module("backend.slack_webhook")
    importlib.reload(module)

    calls = []

    class DummyResponse:
        status_code = 200

        def raise_for_status(self):
            return None

    def fake_post(url, headers=None, json=None, **kwargs):
        calls.append({"url": url, "headers": headers, "json": json, "kwargs": kwargs})
        return DummyResponse()

    module.requests = SimpleNamespace(post=fake_post)
    module.log_alert = lambda *args, **kwargs: None
    module.log_approval = lambda *args, **kwargs: None

    if module.APPROVAL_FILE.exists():
        module.APPROVAL_FILE.unlink()

    client = TestClient(module.app)

    yield module, client, calls

    if module.APPROVAL_FILE.exists():
        module.APPROVAL_FILE.unlink()


def test_slack_interactivity_triggers_workflow(slack_test_app):
    module, client, calls = slack_test_app

    payload = {
        "user": {"name": "alice"},
        "actions": [{"value": "approve_abc123"}],
        "response_url": "https://hooks.slack.com/actions/123",
        "channel": {"id": "C123"},
        "message": {"ts": "1699999999.000100"},
    }
    body = urlencode({"payload": json.dumps(payload)})
    timestamp = "1700000000"
    signature = _signature("signing-secret", timestamp, body)

    response = client.post(
        "/slack/interactivity",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Signature": signature,
            "X-Slack-Request-Timestamp": timestamp,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    urls = [call["url"] for call in calls]
    assert "https://slack.com/api/chat.postMessage" in urls
    assert any(call["url"].startswith("https://api.github.com/repos/example/repo") for call in calls)
    assert any(call["url"].startswith("https://hooks.slack.com/actions/") for call in calls)


def test_validate_quantities_flags_mismatch():
    from backend.validation import validate_quantities

    cad_result = {"items": [{"name": "Concrete", "qty": 110}]} 
    boq_result = {"Concrete": 100}

    diffs = validate_quantities(cad_result, boq_result)

    assert diffs == [
        {
            "item": "Concrete",
            "cad": 110,
            "boq": 100,
            "flag": "Mismatch >5%",
        }
    ]
