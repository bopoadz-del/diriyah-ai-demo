import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.backend.db import Base, get_db
from backend.main import app

import backend.api.learning as learning_api


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    import backend.learning.models  # noqa: F401
    Base.metadata.create_all(engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session, monkeypatch):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(learning_api, "_evaluate_pdp", lambda *args, **kwargs: None)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _create_feedback(client: TestClient, workspace_id: str, label_type: str, label_data: dict):
    response = client.post(
        "/api/learning/feedback",
        json={
            "workspace_id": workspace_id,
            "user_id": 7,
            "source": "ui",
            "input_text": "Route this intent",
            "output_text": "Old output",
            "metadata": {"channel": "web"},
        },
    )
    assert response.status_code == 201
    feedback_id = response.json()["feedback_id"]

    label_resp = client.post(
        f"/api/learning/feedback/{feedback_id}/label",
        json={"label_type": label_type, "label_data": label_data},
    )
    assert label_resp.status_code == 200
    return feedback_id


def test_feedback_create_and_approve(client: TestClient):
    feedback_id = _create_feedback(
        client,
        workspace_id="ws-1",
        label_type="intent_routing",
        label_data={"intent": "project_status"},
    )

    review_resp = client.post(
        f"/api/learning/feedback/{feedback_id}/review",
        json={"reviewer_id": 1, "status": "approved", "notes": "Looks good"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["review_id"]


def test_dataset_export_produces_jsonl_and_manifest(client: TestClient, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LEARNING_EXPORT_DIR", str(tmp_path))
    feedback_id = _create_feedback(
        client,
        workspace_id="ws-2",
        label_type="intent_routing",
        label_data={"intent": "safety_check"},
    )
    client.post(
        f"/api/learning/feedback/{feedback_id}/review",
        json={"reviewer_id": 2, "status": "approved"},
    )

    export_resp = client.post(
        "/api/learning/export-dataset/intent_routing",
        json={"workspace_id": "ws-2"},
    )
    assert export_resp.status_code == 200
    payload = export_resp.json()
    assert payload["record_count"] == 1

    dataset_path = Path(payload["dataset_path"])
    manifest_path = Path(payload["manifest_path"])
    assert dataset_path.exists()
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["dataset_name"] == "intent_routing"
    assert manifest["record_count"] == 1

    jsonl_lines = dataset_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(jsonl_lines) == 1


def test_unapproved_feedback_does_not_export(client: TestClient, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LEARNING_EXPORT_DIR", str(tmp_path))
    _create_feedback(
        client,
        workspace_id="ws-3",
        label_type="tool_routing",
        label_data={"tool": "scheduler"},
    )

    export_resp = client.post(
        "/api/learning/export-dataset/tool_routing",
        json={"workspace_id": "ws-3"},
    )
    assert export_resp.status_code == 200
    payload = export_resp.json()
    assert payload["record_count"] == 0

    dataset_path = Path(payload["dataset_path"])
    assert dataset_path.exists()
    assert dataset_path.read_text(encoding="utf-8") == ""
