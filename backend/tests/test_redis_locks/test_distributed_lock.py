from backend.redisx.locks import DistributedLock


def test_no_redis_allows_lock_release():
    lock = DistributedLock(redis_client=None, redis_url=None)

    token = lock.acquire("lock:test:no-redis", ttl=5)
    assert token is not None
    assert lock.release("lock:test:no-redis", token) is True
