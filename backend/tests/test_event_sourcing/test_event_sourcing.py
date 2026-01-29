import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.backend.db import Base, SessionLocal, engine
from backend.events.envelope import EventEnvelope
from backend.events.models import EventLog, WorkspaceStateProjection
from backend.events.projector import EventProjector
from backend.main import app


@pytest.fixture()
def db_factory():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(test_engine)
    yield TestingSessionLocal
    Base.metadata.drop_all(test_engine)


def test_emit_and_project_hydration_event(db_factory):
    db = db_factory()
    try:
        event = EventEnvelope.create(
            event_type="hydration.completed",
            source="hydration",
            workspace_id=123,
            actor_id=7,
            correlation_id="corr-1",
            payload={"job_id": "job-123"},
        )
        projector = EventProjector()
        applied = projector.apply(event, db, stream="events:global", stream_entry_id="1-0")
        assert applied is True

        log_count = db.query(EventLog).count()
        assert log_count == 1
        projection = db.query(WorkspaceStateProjection).filter_by(workspace_id=123).one()
        assert projection.last_hydration_job_id == "job-123"
        assert projection.last_hydration_at is not None
    finally:
        db.close()


def test_idempotency(db_factory):
    db = db_factory()
    try:
        event_id = str(uuid.uuid4())
        event = EventEnvelope(
            event_id=event_id,
            event_type="hydration.completed",
            ts="2024-01-01T00:00:00Z",
            workspace_id=55,
            actor_id=None,
            correlation_id=None,
            source="hydration",
            payload_json='{"job_id": "job-55"}',
        )
        projector = EventProjector()
        assert projector.apply(event, db, stream="events:global", stream_entry_id="2-0") is True
        assert projector.apply(event, db, stream="events:global", stream_entry_id="2-0") is False
        assert db.query(EventLog).count() == 1
    finally:
        db.close()


def test_api_returns_events():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    event_id = str(uuid.uuid4())
    try:
        db.add(
            EventLog(
                event_id=event_id,
                stream="events:global",
                stream_entry_id="9-0",
                event_type="hydration.completed",
                workspace_id=999,
                actor_id=1,
                correlation_id=None,
                payload_json={"job_id": "job-999"},
            )
        )
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    response = client.get("/api/events/global?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert any(item["event_id"] == event_id for item in data)

    response = client.get("/api/events/workspace/999?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert any(item["event_id"] == event_id for item in data)

    cleanup_db = SessionLocal()
    try:
        cleanup_db.query(EventLog).filter(EventLog.event_id == event_id).delete()
        cleanup_db.commit()
    finally:
        cleanup_db.close()
