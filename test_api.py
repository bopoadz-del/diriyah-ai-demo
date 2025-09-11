"""
Smoke tests for the Diriyah Brain AI application.  These tests
validate that the server starts and basic endpoints respond
successfully.  They do not test integration with external services.
"""

from fastapi.testclient import TestClient
from diriyah_brain_ai.main import app

client = TestClient(app)

def test_root():
    resp = client.get("/")
    assert resp.status_code == 200

def test_ai_query():
    # We use a dummy query and project; service account may not be set
    resp = client.post(
        "/ai/query",
        data={"query": "test", "role": "engineer", "project": "Boulevard"}
    )
    assert resp.status_code == 200
    assert "reply" in resp.json()