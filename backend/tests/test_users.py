from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.main import app  # noqa: E402  (import after path adjustment)

client = TestClient(app)


def test_get_current_user_returns_stub():
    response = client.get("/api/users/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Test User",
        "role": "Engineer",
    }


def test_update_user_returns_stub_acknowledgement():
    response = client.post("/api/users/update")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Updated (stub)"}
