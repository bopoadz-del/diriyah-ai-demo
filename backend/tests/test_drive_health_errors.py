from __future__ import annotations

import importlib
import io
import sys
from contextlib import contextmanager
from types import ModuleType
from typing import Any, Dict, Iterator

from backend.services import google_drive


_FAKE_GOOGLE_MODULES = (
    "google",
    "google.oauth2",
    "google.oauth2.service_account",
    "googleapiclient",
    "googleapiclient.discovery",
    "googleapiclient.http",
)


class _FakeDriveCall:
    """Mimic the ``execute`` wrapper returned by the Google client."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def execute(self) -> Dict[str, Any]:
        return self._payload


class _FakeFilesResource:
    """Minimal stub for the Drive ``files`` resource."""

    def create(self, *, body: Dict[str, Any] | None = None, media_body: Any = None, fields: str | None = None) -> _FakeDriveCall:  # noqa: ARG002
        return _FakeDriveCall({"id": "fake-upload-id"})

    def list(self, **_: Any) -> _FakeDriveCall:
        return _FakeDriveCall({"files": []})


class _FakeDriveService:
    def __init__(self) -> None:
        self._files = _FakeFilesResource()

    def files(self) -> _FakeFilesResource:
        return self._files


class _FakeMediaIoBaseUpload:
    def __init__(self, stream: Any, *, mimetype: str | None = None, resumable: bool = False) -> None:  # noqa: ARG002
        self.stream = stream
        self.mimetype = mimetype
        self.resumable = resumable


class _FakeCredentials:
    @classmethod
    def from_service_account_file(cls, filename: str, scopes: Iterator[str]) -> Dict[str, Any]:  # noqa: ARG003
        return {"filename": filename, "scopes": tuple(scopes)}


@contextmanager
def fake_google_client_modules() -> Iterator[None]:
    """Install lightweight fake Google client modules for the duration of a test."""

    preserved: Dict[str, ModuleType | None] = {name: sys.modules.get(name) for name in _FAKE_GOOGLE_MODULES}

    fake_google = ModuleType("google")
    fake_oauth2 = ModuleType("google.oauth2")
    fake_service_account = ModuleType("google.oauth2.service_account")
    fake_service_account.Credentials = _FakeCredentials  # type: ignore[attr-defined]
    fake_oauth2.service_account = fake_service_account  # type: ignore[attr-defined]
    fake_google.oauth2 = fake_oauth2  # type: ignore[attr-defined]

    fake_api_client = ModuleType("googleapiclient")
    fake_discovery = ModuleType("googleapiclient.discovery")
    fake_discovery.build = lambda *_, **__: _FakeDriveService()  # type: ignore[attr-defined]
    fake_http = ModuleType("googleapiclient.http")
    fake_http.MediaIoBaseUpload = _FakeMediaIoBaseUpload  # type: ignore[attr-defined]
    fake_api_client.discovery = fake_discovery  # type: ignore[attr-defined]
    fake_api_client.http = fake_http  # type: ignore[attr-defined]

    modules_to_install = {
        "google": fake_google,
        "google.oauth2": fake_oauth2,
        "google.oauth2.service_account": fake_service_account,
        "googleapiclient": fake_api_client,
        "googleapiclient.discovery": fake_discovery,
        "googleapiclient.http": fake_http,
    }

    sys.modules.update(modules_to_install)
    importlib.reload(google_drive)

    try:
        yield
    finally:
        for name, original in preserved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
        importlib.reload(google_drive)


def test_upload_attempts_to_initialise_drive_service() -> None:
    """Uploading should try to build the Drive client even when it fails."""

    with fake_google_client_modules():
        original_initialise = google_drive._initialise_service  # type: ignore[attr-defined]
        original_drive_service = google_drive._drive_service  # type: ignore[attr-defined]
        original_service_ready = google_drive._service_ready  # type: ignore[attr-defined]
        google_drive._drive_service = None  # type: ignore[attr-defined]
        google_drive._service_ready = False  # type: ignore[attr-defined]

        calls: list[str] = []

        def fake_initialise() -> Any:
            calls.append("attempted")
            raise RuntimeError("forced failure")

        google_drive._initialise_service = fake_initialise  # type: ignore[attr-defined]

        try:
            dummy_file = io.BytesIO(b"payload")
            upload_id = google_drive.upload_to_drive(dummy_file)
        finally:
            google_drive._initialise_service = original_initialise  # type: ignore[attr-defined]
            google_drive._drive_service = original_drive_service  # type: ignore[attr-defined]
            google_drive._service_ready = original_service_ready  # type: ignore[attr-defined]

        assert upload_id == "stubbed-upload-id"
        assert calls == ["attempted"], "expected the Drive service initialisation to be triggered"
