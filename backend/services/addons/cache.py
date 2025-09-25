import os, pickle, functools, time
import redis

def _client():
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD", None)
    return redis.Redis(host=host, port=port, password=password, decode_responses=False)

def cache(key_prefix: str, ttl: int = 300):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{key_prefix}:{hash((args, tuple(sorted(kwargs.items()))))}"
            r = _client()
            data = r.get(key)
            if data is not None:
                return pickle.loads(data)
            res = fn(*args, **kwargs)
            r.setex(key, ttl, pickle.dumps(res))
            return res
        return wrapper
    return deco
