import time
from typing import Dict, List, Tuple

import pytest
from redis.exceptions import ResponseError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.backend.db import Base
from backend.ops.jobs import enqueue_job
from backend.ops.models import BackgroundJob
from backend.redisx import queue
import backend.jobs.queue_worker as queue_worker


class FakeRedis:
    def __init__(self) -> None:
        self.streams: Dict[str, List[Tuple[str, Dict[str, str]]]] = {}
        self.groups: Dict[str, Dict[str, Dict[str, object]]] = {}
        self._counters: Dict[str, int] = {}
        self.pending: Dict[str, Dict[str, Dict[str, Dict[str, object]]]] = {}

    def _next_id(self, stream: str) -> str:
        self._counters.setdefault(stream, 0)
        self._counters[stream] += 1
        return f"{self._counters[stream]}-0"

    def xadd(self, stream: str, fields: Dict[str, str]):
        entry_id = self._next_id(stream)
        self.streams.setdefault(stream, []).append((entry_id, fields))
        return entry_id

    def xgroup_create(self, stream: str, groupname: str, id: str = "0-0", mkstream: bool = False):
        if mkstream:
            self.streams.setdefault(stream, [])
        self.groups.setdefault(stream, {})
        if groupname in self.groups[stream]:
            raise ResponseError("BUSYGROUP Consumer Group name already exists")
        self.groups[stream][groupname] = {"last_id": id}
        self.pending.setdefault(stream, {})
        self.pending[stream].setdefault(groupname, {})

    def xreadgroup(self, groupname: str, consumername: str, streams: Dict[str, str], count: int = 10, block: int = 0):
        responses = []
        for stream, last_id in streams.items():
            group = self.groups[stream][groupname]
            if last_id != ">":
                start_id = last_id
            else:
                start_id = group["last_id"]
            items = []
            for entry_id, fields in self.streams.get(stream, []):
                if entry_id <= start_id:
                    continue
                items.append((entry_id, fields))
                group["last_id"] = entry_id
                self.pending[stream][groupname][entry_id] = {
                    "consumer": consumername,
                    "fields": fields,
                    "timestamp": time.monotonic(),
                }
                if count and len(items) >= count:
                    break
            if items:
                responses.append((stream, items))
        return responses

    def xack(self, stream: str, groupname: str, entry_id: str):
        self.pending.get(stream, {}).get(groupname, {}).pop(entry_id, None)

    def xautoclaim(
        self,
        stream: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        start_id: str = "0-0",
        count: int = 10,
    ):
        claimed = []
        now = time.monotonic()
        for entry_id, info in list(self.pending.get(stream, {}).get(groupname, {}).items()):
            idle_ms = (now - info["timestamp"]) * 1000
            if idle_ms >= min_idle_time:
                info["consumer"] = consumername
                info["timestamp"] = now
                claimed.append((entry_id, info["fields"]))
                if count and len(claimed) >= count:
                    break
        return start_id, claimed

    def xpending_range(self, stream: str, groupname: str, min: str, max: str, count: int = 10, idle: int = 0):
        pending_items = []
        now = time.monotonic()
        for entry_id, info in self.pending.get(stream, {}).get(groupname, {}).items():
            idle_ms = (now - info["timestamp"]) * 1000
            if idle_ms >= idle:
                pending_items.append((entry_id, info["consumer"], idle_ms, 1))
                if count and len(pending_items) >= count:
                    break
        return pending_items

    def xclaim(self, stream: str, groupname: str, consumername: str, min_idle_time: int, message_ids: List[str]):
        claimed = []
        now = time.monotonic()
        for entry_id in message_ids:
            info = self.pending.get(stream, {}).get(groupname, {}).get(entry_id)
            if not info:
                continue
            info["consumer"] = consumername
            info["timestamp"] = now
            claimed.append((entry_id, info["fields"]))
        return claimed

    def set_pending_idle(self, stream: str, groupname: str, entry_id: str, idle_seconds: int) -> None:
        info = self.pending.get(stream, {}).get(groupname, {}).get(entry_id)
        if info:
            info["timestamp"] = time.monotonic() - idle_seconds


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    import backend.ops.models  # noqa: F401
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
def fake_redis():
    return FakeRedis()


def test_enqueue_creates_db_job_row(db_session, fake_redis):
    job = enqueue_job(
        db_session,
        "hydration",
        {"workspace_id": "ws-1"},
        {"correlation_id": "corr-1", "workspace_id": "ws-1"},
        redis_client=fake_redis,
    )
    stored = db_session.query(BackgroundJob).filter(BackgroundJob.job_id == job.job_id).one()
    assert stored.status == "queued"


def test_worker_consumes_job_success(db_session, fake_redis, session_factory, monkeypatch):
    job = enqueue_job(
        db_session,
        "hydration",
        {"workspace_id": "ws-2"},
        {"correlation_id": "corr-2", "workspace_id": "ws-2"},
        redis_client=fake_redis,
    )

    monkeypatch.setattr(queue_worker, "handle_hydration", lambda *args, **kwargs: {"run_id": 10})

    processed = queue_worker.process_once(
        redis_client=fake_redis,
        db_session_factory=session_factory,
        consumer_name="worker-test",
    )
    assert processed >= 1

    db_session.expire_all()
    stored = db_session.query(BackgroundJob).filter(BackgroundJob.job_id == job.job_id).one()
    assert stored.status == "succeeded"
    assert stored.result_json["run_id"] == 10


def test_worker_retries_then_dlq(db_session, fake_redis, session_factory, monkeypatch):
    job = enqueue_job(
        db_session,
        "hydration",
        {"workspace_id": "ws-3"},
        {"correlation_id": "corr-3", "workspace_id": "ws-3"},
        redis_client=fake_redis,
    )

    monkeypatch.setattr(queue_worker, "handle_hydration", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")))
    monkeypatch.setattr(queue_worker, "BACKOFF_SECONDS", [0, 0, 0, 0, 0])
    monkeypatch.setattr(queue_worker.time, "sleep", lambda *_args, **_kwargs: None)

    queue_worker.process_once(
        redis_client=fake_redis,
        db_session_factory=session_factory,
        consumer_name="worker-test",
    )

    db_session.expire_all()
    stored = db_session.query(BackgroundJob).filter(BackgroundJob.job_id == job.job_id).one()
    assert stored.status == "dlq"
    assert stored.attempts == 5
    assert fake_redis.streams.get(queue.DLQ_STREAM)


def test_claim_stuck_pending(db_session, fake_redis, session_factory, monkeypatch):
    job = enqueue_job(
        db_session,
        "hydration",
        {"workspace_id": "ws-4"},
        {"correlation_id": "corr-4", "workspace_id": "ws-4"},
        redis_client=fake_redis,
    )

    monkeypatch.setattr(queue_worker, "handle_hydration", lambda *args, **kwargs: {"run_id": 99})

    queue.read_batch("worker-a", redis_client=fake_redis)
    pending_id = job.redis_entry_id
    fake_redis.set_pending_idle(queue.STREAM_NAME, queue.GROUP_NAME, pending_id, 120)

    processed = queue_worker.process_once(
        redis_client=fake_redis,
        db_session_factory=session_factory,
        consumer_name="worker-b",
    )
    assert processed >= 1

    db_session.expire_all()
    stored = db_session.query(BackgroundJob).filter(BackgroundJob.job_id == job.job_id).one()
    assert stored.status == "succeeded"
