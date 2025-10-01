from __future__ import annotations

from pytest import MonkeyPatch

from backend.services import google_drive


def test_upload_attempts_to_initialise_drive_service(monkeypatch: MonkeyPatch) -> None:
    attempts: list[str] = []

    def fake_get_drive_service() -> None:
        attempts.append("called")
        raise RuntimeError("service unavailable")

    monkeypatch.setattr(google_drive, "get_drive_service", fake_get_drive_service)

    result = google_drive.upload_to_drive(object())

    assert result == "stubbed-upload-id"
    assert attempts, "expected upload_to_drive to attempt to initialise the Drive service"

