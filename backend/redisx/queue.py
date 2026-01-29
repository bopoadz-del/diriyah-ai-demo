"""Redis Streams queue utilities."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from redis.exceptions import ResponseError

STREAM_NAME = "jobs:main"
DLQ_STREAM = "jobs:dlq"
GROUP_NAME = "jobs"


def _get_redis(redis_url: Optional[str] = None, redis_client: Optional[object] = None):
    if redis_client is not None:
        return redis_client
    url = redis_url or os.getenv("REDIS_URL")
    if not url:
        raise RuntimeError("REDIS_URL is not configured")
    try:
        import redis  # type: ignore

        return redis.Redis.from_url(url)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(f"Failed to initialize Redis client: {exc}") from exc


def ensure_group(redis_client: Optional[object] = None, redis_url: Optional[str] = None) -> None:
    redis_conn = _get_redis(redis_url=redis_url, redis_client=redis_client)
    try:
        redis_conn.xgroup_create(STREAM_NAME, GROUP_NAME, id="0-0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def _serialize_fields(
    job_id: str,
    job_type: str,
    payload: dict,
    headers: dict,
    not_before_at: Optional[datetime] = None,
    priority: Optional[int] = None,
) -> Dict[str, str]:
    fields = {
        "job_id": job_id,
        "job_type": job_type,
        "payload_json": json.dumps(payload),
        "headers_json": json.dumps(headers),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if not_before_at is not None:
        fields["not_before_at"] = not_before_at.isoformat()
    if priority is not None:
        fields["priority"] = str(priority)
    return fields


def enqueue_with_entry_id(
    job_type: str,
    payload: dict,
    headers: dict,
    not_before_at: Optional[datetime] = None,
    priority: Optional[int] = None,
    job_id: Optional[str] = None,
    redis_client: Optional[object] = None,
    redis_url: Optional[str] = None,
) -> Tuple[str, str]:
    redis_conn = _get_redis(redis_url=redis_url, redis_client=redis_client)
    ensure_group(redis_client=redis_conn)
    job_id = job_id or str(uuid.uuid4())
    fields = _serialize_fields(job_id, job_type, payload, headers, not_before_at, priority)
    entry_id = redis_conn.xadd(STREAM_NAME, fields)
    if isinstance(entry_id, bytes):
        entry_id = entry_id.decode("utf-8")
    return job_id, str(entry_id)


def enqueue(
    job_type: str,
    payload: dict,
    headers: dict,
    db: Optional[object] = None,
    not_before_ts: Optional[datetime] = None,
    priority: Optional[int] = None,
    job_id: Optional[str] = None,
    redis_client: Optional[object] = None,
    redis_url: Optional[str] = None,
) -> str:
    job_id, entry_id = enqueue_with_entry_id(
        job_type,
        payload,
        headers,
        not_before_at=not_before_ts,
        priority=priority,
        job_id=job_id,
        redis_client=redis_client,
        redis_url=redis_url,
    )
    if db is not None:
        from backend.ops.models import BackgroundJob, BackgroundJobEvent

        job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).one_or_none()
        if job is None:
            job = BackgroundJob(
                job_id=job_id,
                job_type=job_type,
                workspace_id=payload.get("workspace_id") or headers.get("workspace_id"),
                status="queued",
                redis_stream=STREAM_NAME,
                redis_entry_id=entry_id,
                not_before_at=not_before_ts,
                priority=priority or 0,
            )
            db.add(job)
            db.commit()
            event = BackgroundJobEvent(job_id=job_id, event_type="queued", data_json={"queued_at": datetime.now(timezone.utc).isoformat()})
            db.add(event)
            db.commit()
        else:
            job.redis_entry_id = entry_id
            job.status = "queued"
            job.not_before_at = not_before_ts
            job.priority = priority or job.priority
            job.attempts = 0
            job.last_error = None
            db.commit()
    return job_id


def decode_fields(raw_fields: Dict[object, object]) -> Dict[str, str]:
    decoded: Dict[str, str] = {}
    for key, value in raw_fields.items():
        if isinstance(key, bytes):
            key = key.decode("utf-8")
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        decoded[str(key)] = str(value)
    return decoded


def read_batch(
    consumer_name: str,
    count: int = 10,
    block_ms: int = 2000,
    redis_client: Optional[object] = None,
    redis_url: Optional[str] = None,
) -> List[Tuple[str, Dict[str, str]]]:
    redis_conn = _get_redis(redis_url=redis_url, redis_client=redis_client)
    ensure_group(redis_client=redis_conn)
    response = redis_conn.xreadgroup(
        GROUP_NAME,
        consumer_name,
        {STREAM_NAME: ">"},
        count=count,
        block=block_ms,
    )
    entries: List[Tuple[str, Dict[str, str]]] = []
    for _stream, stream_entries in response or []:
        for entry_id, fields in stream_entries:
            if isinstance(entry_id, bytes):
                entry_id = entry_id.decode("utf-8")
            entries.append((str(entry_id), decode_fields(fields)))
    return entries


def ack(
    entry_id: str,
    redis_client: Optional[object] = None,
    redis_url: Optional[str] = None,
) -> None:
    redis_conn = _get_redis(redis_url=redis_url, redis_client=redis_client)
    redis_conn.xack(STREAM_NAME, GROUP_NAME, entry_id)


def claim_stuck(
    consumer_name: str,
    min_idle_ms: int = 60000,
    count: int = 10,
    redis_client: Optional[object] = None,
    redis_url: Optional[str] = None,
) -> List[Tuple[str, Dict[str, str]]]:
    redis_conn = _get_redis(redis_url=redis_url, redis_client=redis_client)
    ensure_group(redis_client=redis_conn)

    try:
        next_id, entries = redis_conn.xautoclaim(
            STREAM_NAME,
            GROUP_NAME,
            consumer_name,
            min_idle_ms,
            "0-0",
            count=count,
        )
        claimed_entries = entries
    except Exception:
        claimed_entries = _claim_stuck_fallback(
            redis_conn,
            consumer_name,
            min_idle_ms,
            count,
        )

    results: List[Tuple[str, Dict[str, str]]] = []
    for entry_id, fields in claimed_entries or []:
        if isinstance(entry_id, bytes):
            entry_id = entry_id.decode("utf-8")
        results.append((str(entry_id), decode_fields(fields)))
    return results


def _claim_stuck_fallback(
    redis_conn: object,
    consumer_name: str,
    min_idle_ms: int,
    count: int,
) -> List[Tuple[str, Dict[str, str]]]:
    try:
        pending = redis_conn.xpending_range(
            STREAM_NAME,
            GROUP_NAME,
            min="-",
            max="+",
            count=count,
            idle=min_idle_ms,
        )
    except Exception:
        return []
    message_ids = [item[0] for item in pending]
    if not message_ids:
        return []
    return redis_conn.xclaim(
        STREAM_NAME,
        GROUP_NAME,
        consumer_name,
        min_idle_ms,
        message_ids,
    )


def send_to_dlq(
    original_fields: Dict[str, str],
    error: str,
    attempts: int,
    redis_client: Optional[object] = None,
    redis_url: Optional[str] = None,
) -> str:
    redis_conn = _get_redis(redis_url=redis_url, redis_client=redis_client)
    payload = dict(original_fields)
    payload["error"] = error
    payload["attempts"] = str(attempts)
    payload["last_failure_at"] = datetime.now(timezone.utc).isoformat()
    entry_id = redis_conn.xadd(DLQ_STREAM, payload)
    if isinstance(entry_id, bytes):
        entry_id = entry_id.decode("utf-8")
    return str(entry_id)


def get_dlq_entries(
    limit: int = 50,
    redis_client: Optional[object] = None,
    redis_url: Optional[str] = None,
) -> List[Dict[str, str]]:
    redis_conn = _get_redis(redis_url=redis_url, redis_client=redis_client)
    entries = redis_conn.xrevrange(DLQ_STREAM, max="+", min="-", count=limit)
    results: List[Dict[str, str]] = []
    for entry_id, fields in entries:
        decoded = decode_fields(fields)
        decoded["entry_id"] = entry_id.decode("utf-8") if isinstance(entry_id, bytes) else str(entry_id)
        results.append(decoded)
    return results


def replay_from_dlq(
    job_id: Optional[str] = None,
    job_type: Optional[str] = None,
    redis_client: Optional[object] = None,
    redis_url: Optional[str] = None,
    db: Optional[object] = None,
) -> Optional[str]:
    redis_conn = _get_redis(redis_url=redis_url, redis_client=redis_client)
    entries = redis_conn.xrange(DLQ_STREAM, min="-", max="+")
    for entry_id, fields in entries:
        decoded = decode_fields(fields)
        if job_id and decoded.get("job_id") != job_id:
            continue
        if job_type and decoded.get("job_type") != job_type:
            continue
        payload = json.loads(decoded.get("payload_json") or "{}")
        headers = json.loads(decoded.get("headers_json") or "{}")
        return enqueue(
            decoded.get("job_type") or "unknown",
            payload,
            headers,
            db=db,
            not_before_ts=None,
            priority=int(decoded.get("priority") or 0),
            job_id=decoded.get("job_id"),
            redis_client=redis_conn,
        )
    return None


def stats(redis_client: Optional[object] = None, redis_url: Optional[str] = None) -> Dict[str, int]:
    redis_conn = _get_redis(redis_url=redis_url, redis_client=redis_client)
    ensure_group(redis_client=redis_conn)
    pending_count = 0
    consumer_count = 0
    lag = 0
    try:
        pending_info = redis_conn.xpending(STREAM_NAME, GROUP_NAME)
        if isinstance(pending_info, dict):
            pending_count = pending_info.get("pending", 0)
    except Exception:
        pending_count = 0
    try:
        consumers = redis_conn.xinfo_consumers(STREAM_NAME, GROUP_NAME)
        consumer_count = len(consumers or [])
    except Exception:
        consumer_count = 0
    try:
        groups = redis_conn.xinfo_groups(STREAM_NAME)
        for group in groups or []:
            if group.get("name") == GROUP_NAME:
                lag = group.get("lag", 0)
                break
    except Exception:
        lag = 0
    try:
        dlq_count = redis_conn.xlen(DLQ_STREAM)
    except Exception:
        dlq_count = 0
    return {
        "pending_count": int(pending_count or 0),
        "lag": int(lag or 0),
        "consumer_count": int(consumer_count or 0),
        "dlq_count": int(dlq_count or 0),
    }
