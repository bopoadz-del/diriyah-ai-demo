from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.events import router as events_router
from backend.backend.db import Base, get_db
from backend.events.envelope import EventEnvelope
from backend.events.models import EventLog, WorkspaceStateProjection
from backend.events.projector import EventProjector


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    import backend.events.models  # noqa: F401

    Base.metadata.create_all(engine)
    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_client(session_factory):
    app = FastAPI()
    app.include_router(events_router, prefix="/api")

    def _override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    return TestClient(app)


def test_emit_and_project_hydration_event(db_session):
    event = EventEnvelope.build(
        event_type="hydration.completed",
        workspace_id=1,
        source="hydration",
        payload={"job_id": "job-123"},
    )
    applied = EventProjector.apply(event, db_session)
    assert applied is True

    log = db_session.query(EventLog).one()
    assert log.event_type == "hydration.completed"
    projection = (
        db_session.query(WorkspaceStateProjection)
        .filter(WorkspaceStateProjection.workspace_id == 1)
        .one()
    )
    assert projection.last_hydration_job_id == "job-123"
    assert projection.last_hydration_at is not None


def test_idempotency(db_session):
    event = EventEnvelope.build(
        event_type="hydration.completed",
        workspace_id=5,
        source="hydration",
        payload={"job_id": "job-xyz"},
    )
    first = EventProjector.apply(event, db_session)
    second = EventProjector.apply(event, db_session)
    assert first is True
    assert second is False
    assert db_session.query(EventLog).count() == 1
    projection = (
        db_session.query(WorkspaceStateProjection)
        .filter(WorkspaceStateProjection.workspace_id == 5)
        .one()
    )
    assert projection.last_hydration_job_id == "job-xyz"


def test_api_returns_events(db_session, api_client):
    event_one = EventEnvelope.build(
        event_type="hydration.completed",
        workspace_id=123,
        source="hydration",
        payload={"job_id": "job-1"},
    )
    event_two = EventEnvelope.build(
        event_type="learning.dataset.exported",
        workspace_id=123,
        source="learning",
        payload={"dataset_name": "dataset-a", "record_count": 2},
    )
    db_session.add(
        EventLog(
            event_id=event_one.event_id,
            event_type=event_one.event_type,
            ts=event_one.ts,
            workspace_id=event_one.workspace_id,
            actor_id=event_one.actor_id,
            correlation_id=event_one.correlation_id,
            source=event_one.source,
            payload_json=event_one.payload_json,
        )
    )
    db_session.add(
        EventLog(
            event_id=event_two.event_id,
            event_type=event_two.event_type,
            ts=event_two.ts,
            workspace_id=event_two.workspace_id,
            actor_id=event_two.actor_id,
            correlation_id=event_two.correlation_id,
            source=event_two.source,
            payload_json=event_two.payload_json,
        )
    )
    db_session.commit()

    response = api_client.get("/api/events/global?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["event_id"] in {event_one.event_id, event_two.event_id}

    workspace_response = api_client.get("/api/events/workspace/123?limit=10")
    assert workspace_response.status_code == 200
    workspace_payload = workspace_response.json()
    assert len(workspace_payload) == 2
    assert all(item["workspace_id"] == 123 for item in workspace_payload)
