import pytest
from fastapi.testclient import TestClient

import json
from main import app, session_key

client = TestClient(app)


def test_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "It's alive!"}

def test_create_session():
    response = client.post("/create-session", json={"host_name": "test"})
    assert response.status_code == 200
    data = response.json()
    code = data["code"]
    assert len(code) == 6
    assert all(char.isdigit() or char.isupper() for char in code)


def test_get_session():
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    response = client.get(f"/session/{code}")
    assert response.status_code == 200
    data = response.json()
    assert data["host"] == "test"
    assert data["status"] == "waiting"
    assert data["participants"] == ["test"]
    assert data["answers"] == {}

def test_get_session_not_found():
    response = client.get("/session/696969")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"

def test_join_session():
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    join_response = client.post(f"/join-session/{code}", json={"participant_name": "test2"})
    assert join_response.status_code == 200

    # round-trip through Redis
    response = client.get(f"/session/{code}")
    data = response.json()
    assert "test2" in data["participants"]

def test_join_session_not_found():
    response = client.post("/join-session/696969", json={"participant_name": "test"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"

def test_join_session_conflict_revealing(fake_redis):
    code = "ABC123"
    session = {
        "code": code,
        "host": "test",
        "status": "revealing",
        "location": None,
        "participants": ["test"],
        "answers": {},
    }
    fake_redis.set(session_key(code), json.dumps(session), ex=3600)

    response = client.post(f"/join-session/{code}", json={"participant_name": "latecomer"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Uh oh! The group has decided already :("

def test_join_session_conflict_reveal_failed(fake_redis):
    code = "ABC123"
    session = {
        "code": code,
        "host": "test",
        "status": "reveal_failed",
        "location": None,
        "participants": ["test"],
        "answers": {},
    }
    fake_redis.set(session_key(code), json.dumps(session), ex=3600)

    response = client.post(f"/join-session/{code}", json={"participant_name": "latecomer"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Uh oh! The group has decided already :("