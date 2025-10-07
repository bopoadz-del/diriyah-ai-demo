from fastapi.testclient import TestClient

from backend.main import app


def test_parsing_extract_uses_drive_stub() -> None:
    with TestClient(app) as client:
        response = client.get("/api/parsing/extract", params={"file_id": "stub-file"})
        assert response.status_code == 200
        payload = response.json()
    assert payload["status"] == "ok"
    assert "Stub data for Drive file stub-file" in payload["content"]


def test_autocad_takeoff_returns_drive_status() -> None:
    with TestClient(app) as client:
        response = client.get("/api/autocad/takeoff", params={"file_id": "dwg-stub"})
        assert response.status_code == 200
        payload = response.json()
    assert payload["status"] in {"ok", "stubbed"}
    assert payload["result"]["file_id"] == "dwg-stub"
    assert "entities" in payload["result"]


def test_connectors_endpoint_reports_stubbed_drive_sources() -> None:
    with TestClient(app) as client:
        response = client.get("/api/connectors/list")
        assert response.status_code == 200
        payload = response.json()
    assert payload["google_drive"]["status"] in {"connected", "stubbed", "error"}
    assert payload["aconex"]["status"] in {"connected", "stubbed"}
    assert payload["p6"]["status"] in {"connected", "stubbed"}
