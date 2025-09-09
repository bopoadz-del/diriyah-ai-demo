import os
import pytest
from fastapi.testclient import TestClient
from main import app

os.environ.setdefault("OPENAI_API_KEY", "test-key")

client = TestClient(app)

def test_health_version():
    r = client.get("/health"); assert r.status_code == 200 and r.json()["status"] == "ok"
    r = client.get("/version"); assert r.status_code == 200 and r.json()["app"] == "Diriyah Brain AI"

def test_debug_openai():
    r = client.get("/debug/openai")
    assert r.status_code == 200
    assert r.json()["client_type"] == "OpenAI"

def test_upload_txt():
    r = client.post("/upload-file", files={"file": ("a.txt", b"hello")})
    assert r.status_code == 200
    assert r.json()["result"]["text"] == "hello"

def test_projects_list():
    r = client.get("/projects")
    assert r.status_code == 200
    assert isinstance(r.json()["projects"], list)

def test_folders_crud_and_csv():
    payload = {"provider":"google","folder_id":"abc123","display_name":"Opera"}
    r = client.post("/folders/Opera House", json=payload)
    assert r.status_code == 200
    r = client.get("/folders/Opera House")
    assert r.status_code == 200 and r.json()["folder_id"] == "abc123"
    r = client.get("/folders")
    assert r.status_code == 200 and "opera house" in (r.json()["folders"].keys())
    # CSV export
    r = client.get("/exports/folders.csv")
    assert r.status_code == 200
    assert "project_name,provider,folder_id,display_name" in r.text

@pytest.mark.skipif(os.getenv("GOOGLE_OAUTH_JSON") is None, reason="No Google OAuth json")
def test_drive_health_when_configured():
    r = client.get("/drive/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
