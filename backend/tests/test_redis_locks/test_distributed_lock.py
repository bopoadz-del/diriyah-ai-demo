import os
import time
import uuid

import pytest
import redis

from backend.redisx.locks import DistributedLock


@pytest.fixture(scope="module")
def redis_url() -> str:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = redis.Redis.from_url(url, decode_responses=True)
    try:
        client.ping()
    except redis.exceptions.RedisError:
        pytest.skip("Redis is not available for distributed lock tests.")
    return url


def test_acquire_release_ok(redis_url: str) -> None:
    lock = DistributedLock(redis_url=redis_url)
    key = f"test:lock:{uuid.uuid4()}"
    token = lock.acquire(key, ttl=5, wait_seconds=0)
    assert token is not None
    assert lock.release(key, token)


def test_wrong_token_cannot_release(redis_url: str) -> None:
    lock = DistributedLock(redis_url=redis_url)
    key = f"test:lock:{uuid.uuid4()}"
    token = lock.acquire(key, ttl=5, wait_seconds=0)
    assert token is not None
    assert not lock.release(key, "wrong-token")
    assert lock.release(key, token)


def test_ttl_expiry_frees_lock(redis_url: str) -> None:
    lock = DistributedLock(redis_url=redis_url)
    key = f"test:lock:{uuid.uuid4()}"
    token = lock.acquire(key, ttl=1, wait_seconds=0)
    assert token is not None
    time.sleep(1.2)
    token2 = lock.acquire(key, ttl=1, wait_seconds=0)
    assert token2 is not None
    lock.release(key, token2)
