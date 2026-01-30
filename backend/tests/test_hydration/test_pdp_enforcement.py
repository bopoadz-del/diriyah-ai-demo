import json

from fastapi.testclient import TestClient

from backend.main import app
from backend.backend.db import get_db
from backend.hydration.models import HydrationRun, SourceType, WorkspaceSource


def test_pdp_enforcement(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, headers={"X-Tenant-ID": "test-tenant"})

    source = WorkspaceSource(
        workspace_id="ws-1",
        source_type=SourceType.GOOGLE_DRIVE,
        name="Drive",
        config_json=json.dumps({"root_folder_id": "root"}),
    )
    db_session.add(source)
    db_session.commit()

    response = client.post(
        "/api/hydration/run-now",
        headers={"X-User-Id": "999", "X-Tenant-ID": "test-tenant"},
        json={"workspace_id": "ws-1"},
    )

    assert response.status_code == 403
    assert db_session.query(HydrationRun).count() == 0

    app.dependency_overrides.clear()
