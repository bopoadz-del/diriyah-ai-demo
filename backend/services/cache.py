import os, redis, json
from functools import wraps
from typing import Callable, Any
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
def cache(key_prefix: str, ttl: int = 300):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = f"{key_prefix}:{hash((args, frozenset(kwargs.items())))}"
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)
            result = func(*args, **kwargs)
            redis_client.set(key, json.dumps(result), ex=ttl)
            return result
        return wrapper
    return decorator
def health_check():
    try:
        redis_client.ping()
        return {"status": "connected"}
    except redis.exceptions.ConnectionError:
        return {"status": "disconnected"}
