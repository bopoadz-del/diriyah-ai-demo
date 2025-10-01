from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import google_drive


def test_upload_endpoint_returns_debug_metadata(monkeypatch: Any) -> None:
    """The upload endpoint should surface Drive metadata for debugging."""

    def fake_upload(file_obj: Any) -> str:
        assert getattr(file_obj, "filename", None) == "sample.txt"
        return "stubbed-upload-id"

    monkeypatch.setattr(google_drive, "upload_to_drive", fake_upload)
    monkeypatch.setattr(google_drive, "drive_stubbed", lambda: True)
    monkeypatch.setattr(google_drive, "drive_service_ready", lambda: False)
    monkeypatch.setattr(google_drive, "drive_service_error", lambda: "boom")
    monkeypatch.setattr(google_drive, "drive_error_source", lambda: "upload")

    with TestClient(app) as client:
        response = client.post(
            "/api/upload",
            files={"file": ("sample.txt", b"payload", "text/plain")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "filename": "sample.txt",
        "size": 7,
        "status": "stubbed",
        "drive_file_id": "stubbed-upload-id",
        "stubbed": True,
        "error": "boom",
        "service_ready": False,
        "error_source": "upload",
    }


def test_upload_endpoint_marks_uploaded_when_drive_ready(monkeypatch: Any) -> None:
    """Uploads should report a successful status when Drive is available."""

    monkeypatch.setattr(google_drive, "upload_to_drive", lambda file_obj: "real-id")
    monkeypatch.setattr(google_drive, "drive_stubbed", lambda: False)
    monkeypatch.setattr(google_drive, "drive_service_ready", lambda: True)
    monkeypatch.setattr(google_drive, "drive_service_error", lambda: None)
    monkeypatch.setattr(google_drive, "drive_error_source", lambda: None)

    with TestClient(app) as client:
        response = client.post(
            "/api/upload",
            files={"file": ("sample.txt", b"payload", "text/plain")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "filename": "sample.txt",
        "size": 7,
        "status": "uploaded",
        "drive_file_id": "real-id",
        "stubbed": False,
        "error": None,
        "service_ready": True,
        "error_source": None,
    }
