"""
Day 1+ tests — fill these in as you build.

Run: pytest
"""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    """TODO (Day 1): GET / should return 200 and an alive message."""
    pytest.skip("Implement GET / first, then remove this skip")


def test_create_session():
    """TODO (Day 1): POST /create-session returns a 6-char session_code."""
    pytest.skip("Implement POST /create-session first, then remove this skip")


def test_get_session():
    """TODO (Day 1): GET /session/{code} returns the session you created."""
    pytest.skip("Implement GET /session/{code} first, then remove this skip")
