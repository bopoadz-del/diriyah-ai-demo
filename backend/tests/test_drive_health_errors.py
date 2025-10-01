from __future__ import annotations

import importlib
from types import ModuleType, SimpleNamespace

import pytest

import backend.services.google_drive as google_drive


@pytest.fixture
def drive_module() -> ModuleType:
    module = importlib.reload(google_drive)
    try:
        yield module
    finally:
        importlib.reload(google_drive)


def test_upload_attempts_to_initialise_drive_service(drive_module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_get_drive_service() -> None:
        calls.append("get_drive_service")
        raise RuntimeError("expected failure")

    monkeypatch.setattr(drive_module, "get_drive_service", fake_get_drive_service)

    class DummyHandle:
        def __init__(self) -> None:
            self.read_calls = 0
            self.seek_calls = 0

        def read(self) -> bytes:
            self.read_calls += 1
            return b"payload"

        def seek(self, position: int) -> None:
            self.seek_calls += 1
            if position != 0:
                raise AssertionError("unexpected seek position")

    dummy_file = SimpleNamespace(
        file=DummyHandle(),
        filename="dummy.txt",
        content_type="text/plain",
    )

    result = drive_module.upload_to_drive(dummy_file)

    assert result == "stubbed-upload-id"
    assert calls == ["get_drive_service"]
    assert dummy_file.file.read_calls == 0
    assert dummy_file.file.seek_calls == 0
