import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.backend.db import Base, get_db
from backend.events.envelope import EventEnvelope
from backend.events.models import EventLog, WorkspaceStateProjection
from backend.events.projector import EventProjector
from backend.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    import backend.events.models  # noqa: F401
    Base.metadata.create_all(engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_emit_and_project_hydration_event(db_session):
    event = EventEnvelope.build(
        event_type="hydration.completed",
        source="hydration",
        payload={"job_id": "job-1", "files_scanned": 3},
        workspace_id=123,
        actor_id=5,
        correlation_id="corr-1",
        event_id="evt-1",
        ts="2025-01-01T00:00:00+00:00",
    )
    projector = EventProjector()
    applied = projector.apply(event, db_session, stream="events:global", stream_entry_id="1-0")
    assert applied

    log = db_session.query(EventLog).filter(EventLog.event_id == "evt-1").one()
    assert log.stream == "events:global"

    projection = db_session.query(WorkspaceStateProjection).filter(
        WorkspaceStateProjection.workspace_id == 123
    ).one()
    assert projection.last_hydration_job_id == "job-1"


def test_idempotency(db_session):
    event = EventEnvelope.build(
        event_type="regression.promoted",
        source="regression",
        payload={"component": "tool_router"},
        workspace_id=55,
        event_id="evt-2",
        ts="2025-01-01T00:00:00+00:00",
    )
    projector = EventProjector()
    assert projector.apply(event, db_session, stream="events:global", stream_entry_id="2-0")
    assert not projector.apply(event, db_session, stream="events:global", stream_entry_id="2-0")

    count = db_session.query(EventLog).filter(EventLog.event_id == "evt-2").count()
    assert count == 1


def test_api_returns_events(client, db_session):
    db_session.add(
        EventLog(
            event_id="evt-3",
            stream="events:global",
            stream_entry_id="3-0",
            event_type="learning.feedback.created",
            workspace_id=1,
            actor_id=9,
            correlation_id=None,
            payload_json=json.loads('{"feedback_id": 77}'),
        )
    )
    db_session.add(
        EventLog(
            event_id="evt-4",
            stream="events:global",
            stream_entry_id="4-0",
            event_type="hydration.completed",
            workspace_id=2,
            actor_id=None,
            correlation_id=None,
            payload_json=json.loads('{"job_id": "job-2"}'),
        )
    )
    db_session.commit()

    response = client.get("/api/events/global?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2

    workspace_response = client.get("/api/events/workspace/1?limit=10")
    assert workspace_response.status_code == 200
    workspace_payload = workspace_response.json()
    assert len(workspace_payload) == 1
