import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.backend.db import Base
from backend.learning import models as learning_models
from backend.learning.service import add_label, create_feedback, export_dataset, review_feedback

_ = learning_models


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_feedback_create_and_approve(db_session):
    feedback = create_feedback(
        db_session,
        workspace_id="ws1",
        event_type="intent_routing",
        event_payload={"input": "hello"},
        user_id=5,
    )
    label = add_label(db_session, feedback.id, label_type="intent", label_value="greet", labeled_by=7)
    review = review_feedback(db_session, feedback.id, decision="approved", reviewer_id=9)

    assert feedback.id is not None
    assert label.label_value == "greet"
    assert review.decision == "approved"


def test_dataset_export_produces_manifest_and_jsonl(db_session, tmp_path):
    feedback = create_feedback(
        db_session,
        workspace_id="ws_export",
        event_type="intent_routing",
        event_payload={"input": "Book a meeting"},
        user_id=1,
    )
    add_label(db_session, feedback.id, label_type="intent", label_value="schedule_meeting")
    review_feedback(db_session, feedback.id, decision="approved", reviewer_id=2)

    result = export_dataset(
        db_session,
        dataset_name="intent_routing",
        workspace_id="ws_export",
        created_by=2,
        description="Nightly export",
        output_dir=tmp_path,
    )

    assert result.manifest_path.exists()
    assert result.records_path.exists()

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["dataset_name"] == "intent_routing"
    assert manifest["workspace_id"] == "ws_export"
    assert manifest["record_count"] == 1

    records = result.records_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(records) == 1
    record = json.loads(records[0])
    assert record["expected_intent"] == "schedule_meeting"


def test_unapproved_feedback_not_exported(db_session, tmp_path):
    feedback = create_feedback(
        db_session,
        workspace_id="ws_pending",
        event_type="tool_routing",
        event_payload={"input": "Show progress"},
        user_id=3,
    )
    add_label(db_session, feedback.id, label_type="tool", label_value="progress_tracking")

    result = export_dataset(
        db_session,
        dataset_name="tool_routing",
        workspace_id="ws_pending",
        created_by=3,
        output_dir=tmp_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["record_count"] == 0
    assert result.records_path.read_text(encoding="utf-8").strip() == ""
