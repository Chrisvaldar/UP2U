import os
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
import fakeredis
from app import redis_client

@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake_instance = fakeredis.FakeRedis()
    monkeypatch.setattr(redis_client, "r", fake_instance)
    yield fake_instance