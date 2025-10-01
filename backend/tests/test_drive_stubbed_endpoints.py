from __future__ import annotations

import importlib
import sys


def _fresh_google_drive_module():
    module_name = "backend.services.google_drive"
    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    return importlib.reload(module)


def test_drive_stub_details_reflects_latest_error(monkeypatch, tmp_path):
    """drive_stub_details should report the post-check Drive error state."""

    for env_var in ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_SERVICE_ACCOUNT"):
        monkeypatch.delenv(env_var, raising=False)

    missing_credentials = tmp_path / "missing.json"
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(missing_credentials))

    google_drive = _fresh_google_drive_module()

    pre_check_error = google_drive.drive_service_error()
    details_with_missing_credentials = google_drive.drive_stub_details()

    assert details_with_missing_credentials["credentials_available"] is False
    assert details_with_missing_credentials["detail"] == google_drive.drive_service_error()
    assert details_with_missing_credentials["detail"] != pre_check_error

    credential_file = tmp_path / "service_account.json"
    credential_file.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(credential_file))

    monkeypatch.setattr(
        google_drive.service_account.Credentials,
        "from_service_account_file",
        classmethod(lambda cls, *args, **kwargs: object()),
    )

    details_with_present_credentials = google_drive.drive_stub_details()

    assert details_with_present_credentials["credentials_available"] is True
    assert details_with_present_credentials["detail"] == google_drive.drive_service_error()
    assert details_with_present_credentials["detail"] is None
