from pathlib import Path
from typing import List
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.api import openai_test as openai_module


class _DummyModel:
    def __init__(self, identifier: str):
        self.id = identifier


class _DummyResponse:
    def __init__(self, data: List[_DummyModel]):
        self.data = data


def create_client() -> TestClient:
    app = FastAPI()
    app.include_router(openai_module.router, prefix="/api")
    return TestClient(app)


def test_openai_test_missing_api_key(monkeypatch):
    client = create_client()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.get("/api/openai/test")

    assert response.status_code == 200
    assert response.json() == {"status": "error", "message": "OPENAI_API_KEY not set"}


def test_openai_test_with_api_key(monkeypatch):
    client = create_client()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    monkeypatch.setattr(
        openai_module.openai.Model,
        "list",
        lambda: _DummyResponse([
            _DummyModel("model-1"),
            _DummyModel("model-2"),
            _DummyModel("model-3"),
            _DummyModel("model-4"),
        ]),
    )
    monkeypatch.setattr(openai_module, "OPENAI_AVAILABLE", True)

    response = client.get("/api/openai/test")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "models_available": ["model-1", "model-2", "model-3"],
    }
    assert openai_module.openai.api_key == "test-key"
