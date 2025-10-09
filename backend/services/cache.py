import json
import os
from functools import wraps
from typing import Any, Callable

try:  # pragma: no cover - optional dependency for Render debugging
    import redis
except ImportError:  # pragma: no cover - handled gracefully
    redis = None  # type: ignore[assignment]

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = (
    redis.Redis.from_url(REDIS_URL, decode_responses=True) if redis is not None else None
)
def cache(key_prefix: str, ttl: int = 300):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = f"{key_prefix}:{hash((args, frozenset(kwargs.items())))}"
            if redis_client is not None:
                cached = redis_client.get(key)
                if cached:
                    return json.loads(cached)
            result = func(*args, **kwargs)
            if redis_client is not None:
                redis_client.set(key, json.dumps(result), ex=ttl)
            return result
        return wrapper
    return decorator
def health_check():
    if redis_client is None:
        return {"status": "unavailable", "reason": "redis package not installed"}
    try:
        redis_client.ping()
        return {"status": "connected"}
    except redis.exceptions.ConnectionError:
        return {"status": "disconnected"}
