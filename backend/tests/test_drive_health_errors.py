from __future__ import annotations

import importlib
import io
import sys
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
