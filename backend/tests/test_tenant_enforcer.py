from fastapi.testclient import TestClient

from backend.main import app


def test_health_allows_missing_tenant_header(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_options_requests_bypass_tenant_enforcer(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with TestClient(app) as client:
        response = client.options("/api/projects")
    assert response.status_code == 204


def test_protected_endpoint_requires_tenant_header(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with TestClient(app) as client:
        response = client.get("/api/projects")
    assert response.status_code == 403
    assert response.json() == {"detail": "Tenant ID required"}
