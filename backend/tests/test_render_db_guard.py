import importlib
import sys

import pytest


def _import_db_with_env(monkeypatch, env_vars):
    for key in (
        "RENDER",
        "RENDER_SERVICE_ID",
        "RENDER_SERVICE_NAME",
        "DATABASE_URL",
        "SQLITE_PATH",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    sys.modules.pop("backend.backend.db", None)
    return importlib.import_module("backend.backend.db")


def test_render_missing_database_url_raises(monkeypatch):
    with pytest.raises(RuntimeError, match="Render requires Postgres"):
        _import_db_with_env(monkeypatch, {"RENDER_SERVICE_NAME": "svc"})


def test_render_sqlite_database_url_raises(monkeypatch):
    with pytest.raises(RuntimeError, match="Render requires Postgres"):
        _import_db_with_env(
            monkeypatch,
            {"RENDER_SERVICE_NAME": "svc", "DATABASE_URL": "sqlite:///./app.db"},
        )


def test_local_sqlite_allows(monkeypatch):
    module = _import_db_with_env(
        monkeypatch, {"DATABASE_URL": "sqlite:///./app.db"}
    )
    assert module.DATABASE_URL.startswith("sqlite:")
