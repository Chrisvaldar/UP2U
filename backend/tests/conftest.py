import os
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
import fakeredis
import main

@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake_instance = fakeredis.FakeRedis()
    monkeypatch.setattr(main, "r", fake_instance)
    yield