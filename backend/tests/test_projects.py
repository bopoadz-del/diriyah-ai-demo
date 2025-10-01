from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_projects_endpoint_returns_stubbed_payload() -> None:
    with TestClient(app) as client:
        response = client.get("/api/projects")
        assert response.status_code == 200
        payload = response.json()
    assert payload == []
