"""Test that /api/hydration/run-now returns 400 when no sources are configured."""

import json

from fastapi.testclient import TestClient

from backend.main import app
from backend.backend.db import get_db
from backend.hydration.models import SourceType, WorkspaceSource


def test_run_now_no_sources_returns_400(db_session):
    """Run-now should return 400 with clear message when no sources exist."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, headers={"X-Tenant-ID": "test-tenant"})

    response = client.post(
        "/api/hydration/run-now",
        headers={"X-User-Id": "1"},
        json={"workspace_id": "no-sources-workspace"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "No hydration sources configured for workspace" in data["detail"]
    assert "no-sources-workspace" in data["detail"]

    app.dependency_overrides.clear()


def test_run_now_no_enabled_sources_returns_400(db_session):
    """Run-now should return 400 when sources exist but none are enabled."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, headers={"X-Tenant-ID": "test-tenant"})

    # Create a disabled source
    source = WorkspaceSource(
        workspace_id="ws-disabled",
        source_type=SourceType.SERVER_FS,
        name="Disabled Source",
        config_json=json.dumps({"root_path": "/tmp"}),
        is_enabled=False,
    )
    db_session.add(source)
    db_session.commit()

    response = client.post(
        "/api/hydration/run-now",
        headers={"X-User-Id": "1"},
        json={"workspace_id": "ws-disabled"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "No hydration sources configured for workspace" in data["detail"]

    app.dependency_overrides.clear()


def test_run_now_with_enabled_source_not_400(db_session):
    """Run-now should not return 400 when an enabled source exists."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, headers={"X-Tenant-ID": "test-tenant"})

    # Create an enabled source
    source = WorkspaceSource(
        workspace_id="ws-enabled",
        source_type=SourceType.SERVER_FS,
        name="Enabled Source",
        config_json=json.dumps({"root_path": "/tmp"}),
        is_enabled=True,
    )
    db_session.add(source)
    db_session.commit()

    response = client.post(
        "/api/hydration/run-now",
        headers={"X-User-Id": "1"},
        json={"workspace_id": "ws-enabled"},
    )

    # Should fail for other reasons (PDP, Redis), but not 400 for no sources
    assert response.status_code != 400

    app.dependency_overrides.clear()
