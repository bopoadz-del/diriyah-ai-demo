import time
from typing import Callable, Dict, List, Tuple

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.backend.db import Base
from backend.jobs.queue_worker import process_once
from backend.ops.models import BackgroundJob
from backend.redisx.queue import RedisQueue


class FakeRedisResponseError(Exception):
    pass


class FakeRedisStream:
    def __init__(self, time_fn: Callable[[], float] | None = None) -> None:
        self._streams: Dict[str, List[Tuple[str, Dict[str, str]]]] = {}
        self._groups: Dict[Tuple[str, str], Dict[str, Dict[str, Dict[str, float]]]] = {}
        self._ids: Dict[str, int] = {}
        self._time_fn = time_fn or time.monotonic

    def xgroup_create(self, name: str, groupname: str, id: str = "$", mkstream: bool = False):
        if name not in self._streams and mkstream:
            self._streams[name] = []
        key = (name, groupname)
        if key in self._groups:
            raise FakeRedisResponseError("BUSYGROUP Consumer Group name already exists")
        self._groups[key] = {"pending": {}, "last_index": 0}

    def xadd(self, name: str, fields: Dict[str, str]):
        self._streams.setdefault(name, [])
        next_id = self._ids.get(name, 0) + 1
        self._ids[name] = next_id
        entry_id = f"{next_id}-0"
        self._streams[name].append((entry_id, dict(fields)))
        return entry_id

    def xreadgroup(self, groupname: str, consumername: str, streams: Dict[str, str], count: int = 10, block: int = 0):
        results = []
        for stream_name, stream_id in streams.items():
            if stream_id != ">":
                continue
            group_key = (stream_name, groupname)
            group = self._groups[group_key]
            last_index = group["last_index"]
            entries = self._streams.get(stream_name, [])
            new_entries = entries[last_index:last_index + count]
            if new_entries:
                group["last_index"] = last_index + len(new_entries)
                now = self._time_fn()
                for entry_id, _ in new_entries:
                    group["pending"][entry_id] = {
                        "consumer": consumername,
                        "delivered_at": now,
                    }
                results.append((stream_name, new_entries))
        return results

    def xack(self, name: str, groupname: str, entry_id: str):
        group_key = (name, groupname)
        group = self._groups[group_key]
        if entry_id in group["pending"]:
            del group["pending"][entry_id]
            return 1
        return 0

    def xautoclaim(self, name: str, groupname: str, consumername: str, min_idle_time: int, start_id: str = "0-0", count: int = 10):
        group_key = (name, groupname)
        group = self._groups[group_key]
        now = self._time_fn()
        messages = []
        for entry_id, meta in list(group["pending"].items()):
            if len(messages) >= count:
                break
            idle_ms = (now - meta["delivered_at"]) * 1000
            if idle_ms >= min_idle_time:
                meta["consumer"] = consumername
                meta["delivered_at"] = now
                for candidate_id, fields in self._streams.get(name, []):
                    if candidate_id == entry_id:
                        messages.append((candidate_id, fields))
                        break
        return "0-0", messages

    def xpending_range(self, name: str, groupname: str, min: str, max: str, count: int):
        group_key = (name, groupname)
        group = self._groups[group_key]
        now = self._time_fn()
        items = []
        for entry_id, meta in list(group["pending"].items())[:count]:
            idle_ms = int((now - meta["delivered_at"]) * 1000)
            items.append({"message_id": entry_id, "idle": idle_ms})
        return items

    def xclaim(self, name: str, groupname: str, consumername: str, min_idle_time: int, entry_ids: List[str]):
        group_key = (name, groupname)
        group = self._groups[group_key]
        now = self._time_fn()
        claimed = []
        for entry_id in entry_ids:
            meta = group["pending"].get(entry_id)
            if not meta:
                continue
            idle_ms = (now - meta["delivered_at"]) * 1000
            if idle_ms < min_idle_time:
                continue
            meta["consumer"] = consumername
            meta["delivered_at"] = now
            for candidate_id, fields in self._streams.get(name, []):
                if candidate_id == entry_id:
                    claimed.append((candidate_id, fields))
                    break
        return claimed

    @property
    def streams(self):
        return self._streams


@pytest.fixture()
def db_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    import backend.events.models  # noqa: F401
    Base.metadata.create_all(engine)
    yield TestingSessionLocal
    Base.metadata.drop_all(engine)


def _enqueue_job(queue: RedisQueue, db_factory, payload: dict):
    db = db_factory()
    try:
        return queue.enqueue(
            "hydration",
            payload,
            {"correlation_id": "corr-1", "workspace_id": payload["workspace_id"], "user_id": 7},
            db=db,
        )
    finally:
        db.close()


def test_enqueue_and_worker_success(db_factory):
    redis_client = FakeRedisStream()
    queue = RedisQueue(redis_client=redis_client, db_factory=db_factory)
    job_id = _enqueue_job(queue, db_factory, {"workspace_id": "10"})

    def handler(job, payload, headers, db):
        return {
            "files_scanned": 4,
            "docs_added": 2,
            "embeddings_added": 2,
            "duration_sec": 1.2,
            "correlation_id": headers.get("correlation_id"),
        }

    processed = process_once(queue, db_factory=db_factory, hydration_handler=handler, sleep_fn=lambda _: None)
    assert processed == 1

    db = db_factory()
    try:
        job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).one()
        assert job.status == "success"
        assert job.result_json is not None
    finally:
        db.close()


def test_retry_then_dlq(db_factory):
    redis_client = FakeRedisStream()
    queue = RedisQueue(redis_client=redis_client, db_factory=db_factory)
    job_id = _enqueue_job(queue, db_factory, {"workspace_id": "11"})

    def handler(job, payload, headers, db):
        raise RuntimeError("boom")

    for _ in range(6):
        process_once(queue, db_factory=db_factory, hydration_handler=handler, sleep_fn=lambda _: None)

    db = db_factory()
    try:
        job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).one()
        assert job.attempts == 5
        assert job.status == "dlq"
    finally:
        db.close()

    assert len(redis_client.streams.get("jobs:dlq", [])) == 1
