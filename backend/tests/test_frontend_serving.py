from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

import backend.main


def test_frontend_serving_when_build_exists(monkeypatch, tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html><body>OK</body></html>")

    with monkeypatch.context() as env_patch:
        env_patch.setenv("FRONTEND_DIST_DIR", str(dist_dir))
        importlib.reload(backend.main)

        with TestClient(backend.main.app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            assert "OK" in response.text

            health_response = client.get("/health")
            assert health_response.status_code == 200
            assert "application/json" in health_response.headers.get("content-type", "")
            assert health_response.json() == {"status": "ok"}

    importlib.reload(backend.main)
