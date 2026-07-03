import os
import redis

r = redis.Redis.from_url(os.getenv("REDIS_URL"))


def session_key(code: str) -> str:
    return f"session:{code}"
