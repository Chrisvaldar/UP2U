import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")



import pytest

import fakeredis

from app import redis_client
from app.limiter import limiter


@pytest.fixture(autouse=True)
def disable_rate_limiter():
    """
    Disable slowapi rate limiting for tests.

    The limiter uses a separate Redis connection (via REDIS_URL) that is not
    covered by fake_redis. Disabling avoids 429s and Redis connection errors
    in CI and local runs without a Redis service.
    """
    previous = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = previous


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """
    Replace the Redis client with an in-memory fakeredis instance for tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to patch redis_client.r.

    Yields:
        The FakeRedis instance backing all session storage during the test.
    """
    fake_instance = fakeredis.FakeRedis()

    monkeypatch.setattr(redis_client, "r", fake_instance)

    yield fake_instance