"""Utilities for interacting with Google Drive from the backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Final

from google.oauth2 import service_account
from googleapiclient.discovery import build

_SCOPES: Final[list[str]] = ["https://www.googleapis.com/auth/drive"]
_DEFAULT_CREDENTIAL_FILE: Final[str] = "service_account.json"

_DRIVE_SERVICE_ERROR: str | None = None
_DRIVE_CREDENTIAL_ERROR: str | None = None


def _credential_path() -> Path:
    """Return the path to the configured service account credentials."""

    for environment_variable in (
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_SERVICE_ACCOUNT",
    ):
        configured = os.getenv(environment_variable)
        if configured:
            return Path(configured)
    return Path(_DEFAULT_CREDENTIAL_FILE)


def drive_credentials_available() -> bool:
    """Determine whether Drive credentials are available and loadable."""

    global _DRIVE_CREDENTIAL_ERROR

    credential_path = _credential_path()
    if not credential_path.exists():
        _DRIVE_CREDENTIAL_ERROR = (
            f"Google Drive credential file missing: {credential_path}"
        )
        return False

    try:
        service_account.Credentials.from_service_account_file(
            str(credential_path), scopes=_SCOPES
        )
    except Exception as exc:  # pragma: no cover - defensive
        _DRIVE_CREDENTIAL_ERROR = (
            f"Unable to load Google Drive credentials: {exc}".rstrip()
        )
        return False

    _DRIVE_CREDENTIAL_ERROR = None
    return True


def _set_drive_service_error(error: Exception | str | None) -> None:
    """Record the most recent Drive service error for reporting purposes."""

    global _DRIVE_SERVICE_ERROR
    if error is None:
        _DRIVE_SERVICE_ERROR = None
        return
    if isinstance(error, Exception):
        _DRIVE_SERVICE_ERROR = str(error)
    else:
        _DRIVE_SERVICE_ERROR = error


def drive_service_error() -> str | None:
    """Return the latest recorded Drive error message, if any."""

    return _DRIVE_SERVICE_ERROR or _DRIVE_CREDENTIAL_ERROR


def get_drive_service() -> Any:
    """Construct a Google Drive client using service account credentials."""

    credential_path = _credential_path()
    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(credential_path), scopes=_SCOPES
        )
        service = build("drive", "v3", credentials=credentials)
    except Exception as exc:  # pragma: no cover - depends on external SDK
        _set_drive_service_error(exc)
        raise

    _set_drive_service_error(None)
    return service


def drive_stub_details() -> dict[str, Any]:
    """Return diagnostic details for the stubbed Drive implementation."""

    credentials_available = drive_credentials_available()
    detail = drive_service_error()
    return {
        "credentials_available": credentials_available,
        "stubbed": True,
        "detail": detail,
    }
