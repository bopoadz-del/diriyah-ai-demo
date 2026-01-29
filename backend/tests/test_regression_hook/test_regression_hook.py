import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.backend.db import Base
from backend.backend.pdp.schemas import PolicyDecision
from backend.regression.guard import RegressionGuard
from backend.regression.models import CurrentComponentVersion


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    import backend.backend.models  # noqa: F401
    import backend.backend.pdp.models  # noqa: F401
    import backend.events.models  # noqa: F401
    import backend.regression.models  # noqa: F401
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
def guard():
    return RegressionGuard()


def _allow_policy(self, request):
    return PolicyDecision(allowed=True, reason="ok")


def _deny_policy(self, request):
    return PolicyDecision(allowed=False, reason="denied")


def _pass_eval(*_args, **_kwargs):
    return 1, 0.95, 0.9, {"score": 0.95, "min_threshold": 0.9}


def _fail_eval(*_args, **_kwargs):
    return 2, 0.4, 0.9, {"score": 0.4, "min_threshold": 0.9}


def test_non_admin_cannot_approve_or_promote(db_session, guard, monkeypatch):
    import backend.backend.pdp.policy_engine as policy_engine

    monkeypatch.setattr(policy_engine.PolicyEngine, "evaluate", _deny_policy)
    monkeypatch.setattr(guard, "_run_eval_suite", _pass_eval)

    request = guard.create_request(db_session, "intent_router", "candidate:v2", requested_by=1)
    guard.run_check(db_session, request.id)

    with pytest.raises(HTTPException) as excinfo:
        guard.approve(db_session, request.id, approved_by=2)
    assert excinfo.value.status_code == 403

    request.status = "approved"
    db_session.commit()

    with pytest.raises(HTTPException) as excinfo:
        guard.promote(db_session, request.id, actor_id=2)
    assert excinfo.value.status_code == 403


def test_admin_can_approve_and_promote_after_pass(db_session, guard, monkeypatch):
    import backend.backend.pdp.policy_engine as policy_engine

    monkeypatch.setattr(policy_engine.PolicyEngine, "evaluate", _allow_policy)
    monkeypatch.setattr(guard, "_run_eval_suite", _pass_eval)

    request = guard.create_request(db_session, "tool_router", "candidate:v3", requested_by=1)
    guard.run_check(db_session, request.id)

    approved = guard.approve(db_session, request.id, approved_by=10)
    assert approved.status == "approved"

    promoted = guard.promote(db_session, request.id, actor_id=10)
    assert promoted.status == "promoted"

    current = db_session.query(CurrentComponentVersion).filter(CurrentComponentVersion.component == "tool_router").one()
    assert current.current_tag == "candidate:v3"


def test_cannot_approve_without_pass(db_session, guard, monkeypatch):
    import backend.backend.pdp.policy_engine as policy_engine

    monkeypatch.setattr(policy_engine.PolicyEngine, "evaluate", _allow_policy)

    request = guard.create_request(db_session, "ule_linking", "candidate:v4", requested_by=1)
    with pytest.raises(HTTPException) as excinfo:
        guard.approve(db_session, request.id, approved_by=10)
    assert excinfo.value.status_code == 400


def test_fail_blocks_promotion(db_session, guard, monkeypatch):
    import backend.backend.pdp.policy_engine as policy_engine

    monkeypatch.setattr(policy_engine.PolicyEngine, "evaluate", _allow_policy)
    monkeypatch.setattr(guard, "_run_eval_suite", _fail_eval)

    request = guard.create_request(db_session, "pdp_policies", "candidate:v5", requested_by=1)
    guard.run_check(db_session, request.id)

    with pytest.raises(HTTPException) as excinfo:
        guard.approve(db_session, request.id, approved_by=10)
    assert excinfo.value.status_code == 400

    db_session.refresh(request)
    request.status = "approved"
    db_session.commit()

    with pytest.raises(HTTPException) as excinfo:
        guard.promote(db_session, request.id, actor_id=10)
    assert excinfo.value.status_code == 400
