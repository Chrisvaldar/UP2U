import os
import redis

r = redis.Redis.from_url(os.getenv("REDIS_URL"))


def session_key(code: str) -> str:
    """
    Build the Redis key for a session code.

    Args:
        code: Six-character session code.

    Returns:
        Redis key in the form session:{code}.
    """
    return f"session:{code}"
