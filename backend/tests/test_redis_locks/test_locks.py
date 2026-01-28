import time

from backend.redisx.locks import DistributedLock


class FakeRedis:
    def __init__(self) -> None:
        self._store = {}
        self._expiry = {}

    def _purge_expired(self, key: str) -> None:
        expires_at = self._expiry.get(key)
        if expires_at is not None and expires_at <= time.monotonic():
            self._store.pop(key, None)
            self._expiry.pop(key, None)

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        self._purge_expired(key)
        if nx and key in self._store:
            return False
        self._store[key] = value.encode()
        if ex is not None:
            self._expiry[key] = time.monotonic() + ex
        else:
            self._expiry.pop(key, None)
        return True

    def get(self, key: str):
        self._purge_expired(key)
        return self._store.get(key)

    def delete(self, key: str):
        self._purge_expired(key)
        existed = key in self._store
        self._store.pop(key, None)
        self._expiry.pop(key, None)
        return 1 if existed else 0

    def expire(self, key: str, ttl: int):
        self._purge_expired(key)
        if key not in self._store:
            return 0
        self._expiry[key] = time.monotonic() + ttl
        return 1

    def eval(self, script: str, numkeys: int, key: str, token: str, *args):
        self._purge_expired(key)
        stored = self._store.get(key)
        token_bytes = token.encode()

        if "expire" in script:
            if stored == token_bytes:
                ttl = int(args[0]) if args else 0
                return self.expire(key, ttl)
            return 0
        if "del" in script:
            if stored == token_bytes:
                return self.delete(key)
            return 0
        raise ValueError("Unexpected script")


def test_acquire_release_ok():
    redis = FakeRedis()
    lock = DistributedLock(redis_client=redis)

    token = lock.acquire("lock:test", ttl=5)
    assert token
    assert lock.release("lock:test", token) is True
    assert redis.get("lock:test") is None


def test_wrong_token_cannot_release():
    redis = FakeRedis()
    lock = DistributedLock(redis_client=redis)

    token = lock.acquire("lock:test", ttl=5)
    assert token
    assert lock.release("lock:test", "wrong-token") is False
    assert redis.get("lock:test") is not None
    assert lock.acquire("lock:test", ttl=5) is None


def test_ttl_expiry_frees_lock():
    redis = FakeRedis()
    lock = DistributedLock(redis_client=redis)

    token = lock.acquire("lock:test", ttl=1)
    assert token
    time.sleep(1.1)
    new_token = lock.acquire("lock:test", ttl=1)
    assert new_token
    assert new_token != token
