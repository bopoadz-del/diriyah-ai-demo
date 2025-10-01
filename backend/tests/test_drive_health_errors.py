import io
from types import SimpleNamespace

import pytest

from backend.services import google_drive


class DummyMedia:
    def __init__(self, stream, mimetype, resumable=False):  # noqa: D401 - simple stub
        self.stream = stream
        self.mimetype = mimetype
        self.resumable = resumable


class DummyDriveRequest:
    def __init__(self, call_log):
        self._call_log = call_log

    def execute(self):
        self._call_log.append("execute")
        return {"id": "real-file-id"}


class DummyDriveFiles:
    def __init__(self, call_log):
        self._call_log = call_log

    def create(self, body, media_body, fields):
        self._call_log.append(("create", body["name"], fields))
        assert isinstance(media_body, DummyMedia)
        return DummyDriveRequest(self._call_log)


class DummyDriveService:
    def __init__(self, call_log):
        self._call_log = call_log

    def files(self):
        self._call_log.append("files")
        return DummyDriveFiles(self._call_log)


@pytest.fixture()
def upload_file():
    return SimpleNamespace(
        file=io.BytesIO(b"payload"),
        filename="document.txt",
        content_type="text/plain",
    )


def test_upload_attempts_service_before_stub(monkeypatch, upload_file):
    call_log = []

    def fake_get_drive_service():
        call_log.append("get_drive_service")
        return DummyDriveService(call_log)

    monkeypatch.setattr(google_drive, "get_drive_service", fake_get_drive_service)
    monkeypatch.setattr(google_drive, "MediaIoBaseUpload", DummyMedia)

    file_id = google_drive.upload_to_drive(upload_file)

    assert file_id == "real-file-id"
    assert call_log[0] == "get_drive_service"
    assert call_log[-1] == "execute"


def test_stub_path_used_after_service_failure(monkeypatch, upload_file):
    call_log = []

    def failing_get_drive_service():
        call_log.append("get_drive_service")
        raise RuntimeError("boom")

    monkeypatch.setattr(google_drive, "get_drive_service", failing_get_drive_service)
    monkeypatch.setattr(google_drive, "MediaIoBaseUpload", DummyMedia)

    file_id = google_drive.upload_to_drive(upload_file)

    assert file_id == google_drive.STUB_FILE_ID
    assert call_log == ["get_drive_service"]
