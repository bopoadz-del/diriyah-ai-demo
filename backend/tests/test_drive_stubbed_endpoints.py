"""Regression coverage for stubbed Google Drive behaviour."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from backend.api import projects
from backend.main import app
from backend.services import google_drive


@pytest.fixture()
def stubbed_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Return a client with Google credentials pointing to a missing file."""

    missing_path = Path("/tmp/google-credentials-missing.json")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(missing_path))
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_missing_credentials(stubbed_client: TestClient) -> None:
    response = stubbed_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["drive"]["credentials_available"] is False
    # service_error should be recorded even before any Drive call
    assert "Credentials" in payload["drive"]["service_error"]
    assert payload["drive"]["stubbed"] is True


def test_upload_endpoint_stubbed(stubbed_client: TestClient) -> None:
    response = stubbed_client.post(
        "/api/upload",
        files={"file": ("demo.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "stubbed"
    assert payload["file_id"] == google_drive.STUB_FILE_ID
    assert payload["detail"] == google_drive.drive_service_error()
    assert payload["credentials_available"] is False


def test_speech_endpoint_stubbed(stubbed_client: TestClient) -> None:
    response = stubbed_client.post(
        "/api/speech",
        files={"file": ("voice.wav", b"audio-bytes", "audio/wav")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "stubbed"
    assert payload["file_id"] == google_drive.STUB_FILE_ID
    assert "text" in payload
    assert payload["detail"] == google_drive.drive_service_error()
    assert payload["credentials_available"] is False


def test_vision_endpoint_stubbed(stubbed_client: TestClient) -> None:
    response = stubbed_client.post(
        "/api/vision",
        files={"file": ("image.png", b"png-bytes", "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "stubbed"
    assert payload["file_id"] == google_drive.STUB_FILE_ID
    assert payload["detections"] == []
    assert payload["detail"] == google_drive.drive_service_error()
    assert payload["credentials_available"] is False


def test_projects_endpoint_stubbed(monkeypatch: pytest.MonkeyPatch, stubbed_client: TestClient) -> None:
    monkeypatch.setattr(projects, "USE_FIXTURE_PROJECTS", False)
    response = stubbed_client.get("/api/projects")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "stubbed"
    assert payload["projects"] == google_drive.STUB_FOLDERS
    assert payload["detail"] == google_drive.drive_service_error()
    assert payload["credentials_available"] is False


def test_drive_scan_endpoint_stubbed(stubbed_client: TestClient) -> None:
    response = stubbed_client.get("/api/projects/scan-drive")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "stubbed"
    assert payload["projects"] == []
    assert payload["detail"] == google_drive.drive_service_error()
    assert payload["credentials_available"] is False


def test_drive_diagnose_endpoint_stubbed(stubbed_client: TestClient) -> None:
    response = stubbed_client.get("/api/drive/diagnose")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "stubbed"
    assert payload["projects"] == google_drive.STUB_FOLDERS
    assert payload["detail"] == google_drive.drive_service_error()
    assert payload["credentials_available"] is False
