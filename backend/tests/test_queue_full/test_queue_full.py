import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.exceptions import ResponseError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.backend.db import Base
from backend.hydration.models import SourceType, WorkspaceSource
from backend.jobs import scheduler_worker
from backend.ops.models import BackgroundJob, BackgroundJobEvent
from backend.redisx import queue
import backend.jobs.queue_worker as queue_worker
import backend.api.ops_queue as ops_queue


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

    def xlen(self, stream: str):
        return len(self.streams.get(stream, []))

    def xrange(self, stream: str, min: str = "-", max: str = "+"):
        return list(self.streams.get(stream, []))

    def xrevrange(self, stream: str, max: str = "+", min: str = "-", count: int = 10):
        entries = list(reversed(self.streams.get(stream, [])))
        return entries[:count]

    def xgroup_create(self, stream: str, groupname: str, id: str = "0-0", mkstream: bool = False):
        if mkstream:
            self.streams.setdefault(stream, [])
        self.groups.setdefault(stream, {})
        if groupname in self.groups[stream]:
            raise ResponseError("BUSYGROUP Consumer Group name already exists")
        self.groups[stream][groupname] = {"last_id": id, "consumers": set()}
        self.pending.setdefault(stream, {})
        self.pending[stream].setdefault(groupname, {})

    def xreadgroup(self, groupname: str, consumername: str, streams: Dict[str, str], count: int = 10, block: int = 0):
        responses = []
        for stream, last_id in streams.items():
            group = self.groups[stream][groupname]
            group["consumers"].add(consumername)
            start_id = group["last_id"] if last_id == ">" else last_id
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

    def xpending(self, stream: str, groupname: str):
        pending_count = len(self.pending.get(stream, {}).get(groupname, {}))
        return {"pending": pending_count}

    def xinfo_consumers(self, stream: str, groupname: str):
        group = self.groups.get(stream, {}).get(groupname, {})
        return [{"name": name} for name in group.get("consumers", set())]

    def xinfo_groups(self, stream: str):
        groups = []
        for name, group in self.groups.get(stream, {}).items():
            last_id = group.get("last_id", "0-0")
            last_index = int(last_id.split("-")[0]) if last_id else 0
            lag = max(len(self.streams.get(stream, [])) - last_index, 0)
            groups.append({"name": name, "lag": lag})
        return groups


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    import backend.ops.models  # noqa: F401
    import backend.hydration.models  # noqa: F401
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


def test_dispatch_multi_job_types(db_session, session_factory, fake_redis, monkeypatch):
    results = []

    def handler_factory(job_type):
        def _handler(payload, headers, db):
            results.append(job_type)
            return {"job_type": job_type}

        return _handler

    def fake_get_handler(job_type):
        return handler_factory(job_type)

    monkeypatch.setattr(queue_worker, "get_handler", fake_get_handler)

    job_types = ["hydration", "learning", "evaluation", "tool_run"]
    for idx, job_type in enumerate(job_types):
        queue.enqueue(
            job_type,
            {"workspace_id": f"ws-{idx}"},
            {"workspace_id": f"ws-{idx}"},
            db=db_session,
            redis_client=fake_redis,
        )

    processed = queue_worker.process_once(
        redis_client=fake_redis,
        db_session_factory=session_factory,
        consumer_name="worker-test",
    )
    assert processed == len(job_types)
    assert sorted(results) == sorted(job_types)

    db_session.expire_all()
    statuses = [job.status for job in db_session.query(BackgroundJob).all()]
    assert all(status == "succeeded" for status in statuses)


def test_scheduler_enqueues_nightly_hydration(db_session, fake_redis):
    source = WorkspaceSource(
        workspace_id="ws-10",
        source_type=SourceType.SERVER_FS,
        name="Test",
        config_json="{}",
        secrets_ref=None,
        is_enabled=True,
    )
    db_session.add(source)
    db_session.commit()

    count = scheduler_worker.process_once(db=db_session, redis_client=fake_redis)
    assert count == 1

    job = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "hydration").one()
    assert job.status == "queued"

    events = db_session.query(BackgroundJobEvent).filter(BackgroundJobEvent.job_id == job.job_id).all()
    event_types = {event.event_type for event in events}
    assert "scheduled" in event_types
    assert "enqueued" in event_types


def test_dlq_replay_reenqueues(db_session, session_factory, fake_redis, monkeypatch):
    def fake_get_handler(job_type):
        return lambda payload, headers, db: {"job_type": job_type}

    monkeypatch.setattr(queue_worker, "get_handler", fake_get_handler)

    job_id = queue.enqueue(
        "learning",
        {"workspace_id": "ws-20"},
        {"workspace_id": "ws-20"},
        db=db_session,
        redis_client=fake_redis,
    )
    fields = {
        "job_id": job_id,
        "job_type": "learning",
        "payload_json": '{"workspace_id": "ws-20"}',
        "headers_json": '{"workspace_id": "ws-20"}',
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    queue.send_to_dlq(fields, "boom", 5, redis_client=fake_redis)

    replayed = queue.replay_from_dlq(job_id=job_id, db=db_session, redis_client=fake_redis)
    assert replayed == job_id

    processed = queue_worker.process_once(
        redis_client=fake_redis,
        db_session_factory=session_factory,
        consumer_name="worker-test",
    )
    assert processed >= 1

    db_session.expire_all()
    job = db_session.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).one()
    assert job.status == "succeeded"


def test_stats_endpoint_returns_values(fake_redis, monkeypatch):
    app = FastAPI()
    app.include_router(ops_queue.router, prefix="/api")

    original_stats = queue.stats
    monkeypatch.setattr(ops_queue.queue, "stats", lambda: original_stats(redis_client=fake_redis))

    client = TestClient(app)
    response = client.get("/api/ops/queue/stats")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"pending_count", "lag", "consumer_count", "dlq_count"}
