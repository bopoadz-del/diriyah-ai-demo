from __future__ import annotations

 codex/add-test-body-for-upload_attempts_to_initialise_drive_servic
from pytest import MonkeyPatch

import importlib
import io
import sys
 codex/recreate-missing-test-for-google-drive-service
from contextlib import contextmanager
from types import ModuleType
from typing import Any, Dict, Iterator
 main

from backend.services import google_drive


 codex/add-test-body-for-upload_attempts_to_initialise_drive_servic
def test_upload_attempts_to_initialise_drive_service(monkeypatch: MonkeyPatch) -> None:
    attempts: list[str] = []

    def fake_get_drive_service() -> None:
        attempts.append("called")
        raise RuntimeError("service unavailable")

    monkeypatch.setattr(google_drive, "get_drive_service", fake_get_drive_service)

    result = google_drive.upload_to_drive(object())

    assert result == "stubbed-upload-id"
    assert attempts, "expected upload_to_drive to attempt to initialise the Drive service"


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

import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _install_fake_google_modules() -> dict[str, types.ModuleType | None]:
    """Inject minimal fake Google client modules for testing."""

    build_error = RuntimeError("build exploded")

    google_pkg = types.ModuleType("google")
    google_pkg.__path__ = []  # type: ignore[attr-defined]
    oauth2_module = types.ModuleType("google.oauth2")
    service_account_module = types.ModuleType("google.oauth2.service_account")

    class _FakeCredentials:
        @classmethod
        def from_service_account_file(cls, *args, **kwargs):  # type: ignore[no-untyped-def]
            return object()

    service_account_module.Credentials = _FakeCredentials  # type: ignore[attr-defined]
    oauth2_module.service_account = service_account_module  # type: ignore[attr-defined]
    google_pkg.oauth2 = oauth2_module  # type: ignore[attr-defined]

    googleapiclient_pkg = types.ModuleType("googleapiclient")
    googleapiclient_pkg.__path__ = []  # type: ignore[attr-defined]
    discovery_module = types.ModuleType("googleapiclient.discovery")

    def _failing_build(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise build_error

    discovery_module.build = _failing_build  # type: ignore[attr-defined]
    http_module = types.ModuleType("googleapiclient.http")

    class _FakeUpload:  # pragma: no cover - simple stub
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            pass

    http_module.MediaIoBaseUpload = _FakeUpload  # type: ignore[attr-defined]
    googleapiclient_pkg.discovery = discovery_module  # type: ignore[attr-defined]
    googleapiclient_pkg.http = http_module  # type: ignore[attr-defined]

    injected = {
        "google": google_pkg,
        "google.oauth2": oauth2_module,
        "google.oauth2.service_account": service_account_module,
        "googleapiclient": googleapiclient_pkg,
        "googleapiclient.discovery": discovery_module,
        "googleapiclient.http": http_module,
    }

    previous: dict[str, types.ModuleType | None] = {}
    for name, module in injected.items():
        previous[name] = sys.modules.get(name)
        sys.modules[name] = module
    return previous


def _restore_modules(previous: dict[str, types.ModuleType | None]) -> None:
    """Restore modules that were temporarily replaced during the test."""

    for name, module in previous.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


@pytest.mark.usefixtures("tmp_path")
def test_health_reports_non_credential_drive_error(monkeypatch, tmp_path):
    """Ensure credential checks do not clear non-credential Drive errors."""

    credential_file = Path(tmp_path) / "service_account.json"
    credential_file.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT", str(credential_file))

    import backend.services.google_drive as google_drive_module
    import backend.main as backend_main_module

    previous_modules = _install_fake_google_modules()

    try:
        google_drive = importlib.reload(google_drive_module)
        backend_main = importlib.reload(backend_main_module)

        with pytest.raises(RuntimeError):
            google_drive.get_drive_service()

        # Credential probes should not wipe the recorded non-credential error.
        assert google_drive.drive_credentials_available() is True
        assert google_drive.drive_service_error() is not None
        assert google_drive.drive_credentials_available() is True
        recorded_error = google_drive.drive_service_error()
        assert recorded_error is not None and "build exploded" in recorded_error

        with TestClient(backend_main.app) as client:
            response = client.get("/health")
        payload = response.json()
        assert payload["drive"]["credentials_available"] is True
        assert payload["drive"]["stubbed"] is True
        assert "build exploded" in (payload["drive"].get("error") or "")
    finally:
        _restore_modules(previous_modules)
        importlib.reload(google_drive_module)
        importlib.reload(backend_main_module)


def test_upload_attempts_to_initialise_drive_service(monkeypatch):
    """Ensure uploads try to build the Drive service before using the stub."""

    import backend.services.google_drive as google_drive_module

    google_drive = importlib.reload(google_drive_module)

    call_count = 0

    def _failing_get_drive_service():  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        raise RuntimeError("boom")

    class _FakeUpload:  # pragma: no cover - trivial shim for instantiation
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            pass

    monkeypatch.setattr(google_drive, "get_drive_service", _failing_get_drive_service)
    monkeypatch.setattr(google_drive, "MediaIoBaseUpload", _FakeUpload)

    try:
        result = google_drive.upload_to_drive(io.BytesIO(b"payload"))
    finally:
        importlib.reload(google_drive_module)

    assert result == "stubbed-upload-id"
    assert call_count == 1
 main
main
