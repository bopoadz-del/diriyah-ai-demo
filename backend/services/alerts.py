"""Alert helpers for webhook integrations."""
from __future__ import annotations

import os
from typing import Any, Dict

try:  # pragma: no cover - optional dependency for lightweight Render builds
    import requests
except ModuleNotFoundError:  # pragma: no cover - handled gracefully at runtime
    class _RequestsStub:
        class exceptions:  # pragma: no cover - simple namespace
            class ConnectionError(Exception):
                """Fallback connection error when requests is unavailable."""

        def post(self, *_args, **_kwargs):  # pragma: no cover - tests monkeypatch
            raise RuntimeError("requests package not installed")

    requests = _RequestsStub()  # type: ignore[assignment]
    _REQUESTS_AVAILABLE = False
else:
    _REQUESTS_AVAILABLE = True

WebhookResult = Dict[str, str]


def _post_webhook(url: str, payload: Dict[str, Any]) -> WebhookResult:
    """Send ``payload`` to ``url`` and normalise the response."""
    if not hasattr(requests, "post"):
        return {
            "status": "error",
            "reason": "requests package not installed",
        }
    try:
        response = requests.post(url, json=payload, timeout=5)
    except requests.RequestException as exc:  # pragma: no cover - requests handles errors
        return {"status": "error", "reason": str(exc)}
    if response.status_code == 200:
        return {"status": "sent"}
    result: WebhookResult = {
        "status": "error",
        "code": str(response.status_code),
    }
    if response.text:
        result["response"] = response.text[:200]
    return result


def send_alert(message: str, *, level: str = "info") -> Dict[str, Any]:
    """Send ``message`` to any configured webhook integrations."""

    slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    teams_webhook = os.getenv("TEAMS_WEBHOOK_URL", "").strip()

    configured_targets = {}

    if slack_webhook:
        configured_targets["slack"] = {
            **_post_webhook(slack_webhook, {"text": message}),
            "channel": "slack",
        }

    if teams_webhook:
        configured_targets["teams"] = {
            **_post_webhook(teams_webhook, {"text": message}),
            "channel": "teams",
        }

    if not configured_targets:
        return {
            "status": "skipped",
            "reason": "No webhook configured",
            "message": message,
            "level": level,
        }

    successes = [name for name, result in configured_targets.items() if result["status"] == "sent"]

    if successes:
        status = "sent"
    elif configured_targets:
        status = "error"
    else:
        status = "skipped"

    result_payload: Dict[str, Any] = {
        "status": status,
        "message": message,
        "level": level,
        "targets": configured_targets,
    }

    if not successes:
        result_payload["reason"] = "All webhook deliveries failed"
    elif len(successes) != len(configured_targets):
        result_payload["reason"] = "One or more webhook deliveries failed"

    return result_payload
