import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.chat import router as chat_router
from backend.services.vector_memory import set_active_project


class _MockCollection:
    """Predictable collection used to validate chat integration."""

    def __init__(self):
        self.queries = []

    def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub
        self.queries.append({"query_texts": query_texts, "n_results": n_results})
        return {"documents": [["Doc snippet"]]}


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(chat_router, prefix="/api")
    with TestClient(app) as test_client:
        yield test_client


def test_chat_without_active_project(client):
    """Chat endpoint should handle missing active project gracefully."""

    set_active_project(None)

    response = client.post("/api/chat", data={"message": "Hello"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["project_id"] is None
    assert payload["intent"]["project_id"] is None


def test_chat_with_empty_documents(client):
    """Chat endpoint should handle empty document results gracefully."""

    class EmptyDocumentsCollection:
        def query(self, *, query_texts, n_results):  # pragma: no cover - simple stub
            return {"documents": []}

    set_active_project({"id": "proj-123", "collection": EmptyDocumentsCollection()})
    try:
        response = client.post("/api/chat", data={"message": "Hello"})
    finally:
        set_active_project(None)

    assert response.status_code == 200

    payload = response.json()
    assert payload["context_docs"] == []


def test_chat_with_active_project_collection(client):
    """Chat endpoint should return project context when collection is active."""

    collection = _MockCollection()
    set_active_project({"id": "proj-123", "collection": collection})

    try:
        response = client.post("/api/chat", data={"message": "Hello"})
    finally:
        set_active_project(None)

    assert response.status_code == 200

    payload = response.json()
    assert payload["project_id"] == "proj-123"
    assert payload["context_docs"] == ["Doc snippet"]
    assert payload["response"].endswith("proj-123")
    assert collection.queries == [{"query_texts": ["Hello"], "n_results": 3}]
