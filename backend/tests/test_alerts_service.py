"""Tests for webhook alert delivery helpers."""
from __future__ import annotations

from typing import Any

import pytest

from backend.services import alerts


class _Response:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def test_send_alert_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)

    result = alerts.send_alert("Check pumps")

    assert result["status"] == "skipped"
    assert result["reason"] == "No webhook configured"
    assert "targets" not in result


def test_send_alert_slack_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)

    def fake_post(url: str, *, json: Any, timeout: int) -> _Response:  # type: ignore[override]
        assert url.startswith("https://hooks.slack.com/services/")
        assert json == {"text": "Deploy complete"}
        assert timeout == 5
        return _Response(200)

    monkeypatch.setattr(alerts.requests, "post", fake_post)

    result = alerts.send_alert("Deploy complete")

    assert result["status"] == "sent"
    assert result["targets"]["slack"]["status"] == "sent"
    assert "reason" not in result


def test_send_alert_partial_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/fail")
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://outlook.office.com/webhook/ok")

    def fake_post(url: str, *, json: Any, timeout: int) -> _Response:  # type: ignore[override]
        if url.endswith("/fail"):
            return _Response(500, "slack error")
        return _Response(200)

    monkeypatch.setattr(alerts.requests, "post", fake_post)

    result = alerts.send_alert("HVAC offline")

    assert result["status"] == "sent"
    assert result["targets"]["slack"]["status"] == "error"
    assert result["targets"]["teams"]["status"] == "sent"
    assert result["reason"] == "One or more webhook deliveries failed"


def test_send_alert_all_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/fail")
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://outlook.office.com/webhook/fail")

    def fake_post(url: str, *, json: Any, timeout: int) -> _Response:  # type: ignore[override]
        return _Response(400, "bad request")

    monkeypatch.setattr(alerts.requests, "post", fake_post)

    result = alerts.send_alert("Sensor fault")

    assert result["status"] == "error"
    assert result["reason"] == "All webhook deliveries failed"
    assert all(target["status"] == "error" for target in result["targets"].values())
