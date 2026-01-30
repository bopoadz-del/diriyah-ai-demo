from fastapi.testclient import TestClient

from backend.main import app


def test_health_allows_missing_tenant() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_options_allows_missing_tenant() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/projects",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code in {200, 204}


def test_missing_tenant_is_blocked() -> None:
    with TestClient(app) as client:
        response = client.get("/api/projects")
    assert response.status_code == 403
    assert response.json() == {"detail": "Tenant ID required"}


def test_tenant_header_allows_protected_route() -> None:
    with TestClient(app, headers={"X-Tenant-ID": "test-tenant"}) as client:
        response = client.get("/api/projects")
    assert response.status_code != 403
