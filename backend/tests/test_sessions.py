import pytest
from fastapi.testclient import TestClient

import json
import main

client = TestClient(main.app)


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

    join_response = client.post(
        f"/join-session/{code}", json={"participant_name": "test2"}
    )
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
    fake_redis.set(main.session_key(code), json.dumps(session), ex=3600)

    response = client.post(
        f"/join-session/{code}", json={"participant_name": "latecomer"}
    )
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
    fake_redis.set(main.session_key(code), json.dumps(session), ex=3600)

    response = client.post(
        f"/join-session/{code}", json={"participant_name": "latecomer"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Uh oh! The group has decided already :("


def test_end_session():
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    end_response = client.post(f"/end-session/{code}", json={"host_name": "test"})
    assert end_response.status_code == 200

    response = client.get(f"/session/{code}")
    assert response.status_code == 404


def test_end_session_not_host():
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    end_response = client.post(f"/end-session/{code}", json={"host_name": "test2"})
    assert end_response.status_code == 403

    response = client.get(f"/session/{code}")
    assert response.status_code == 200


def test_end_session_not_found():
    response = client.post(f"/end-session/696969", json={"host_name": "test"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_ttl_preserved_on_join(fake_redis):
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    ttl_before = fake_redis.ttl(main.session_key(code))

    client.post(f"/join-session/{code}", json={"participant_name": "test2"})

    ttl_after = fake_redis.ttl(main.session_key(code))

    assert ttl_before - ttl_after < 5


def test_start_session(monkeypatch):
    monkeypatch.setattr(
        main, "location_to_cuisines", lambda lat, lng: ["thai", "italian"]
    )

    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    start_response = client.post(
        f"/start-session/{code}", json={"host_name": "test", "lat": 0, "lng": 0}
    )
    assert start_response.status_code == 200
    data = start_response.json()
    assert data["status"] == "active"
    assert data["cuisines"] == ["thai", "italian"]


def test_start_session_not_host():
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    start_response = client.post(
        f"/start-session/{code}", json={"host_name": "test2", "lat": 0, "lng": 0}
    )
    assert start_response.status_code == 403
    assert start_response.json()["detail"] == "Only the host can start the session."


def test_start_session_not_found():
    response = client.post(
        f"/start-session/696969", json={"host_name": "test", "lat": 0, "lng": 0}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"

def test_start_session_places_failure(monkeypatch):
    def raise_bad_response(lat, lng):
        raise main.UpstreamBadResponse("places failed")

    monkeypatch.setattr(main, "location_to_cuisines", raise_bad_response)

    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    start_response = client.post(f"/start-session/{code}", json={"host_name": "test", "lat": 0, "lng": 0})
    assert start_response.status_code == 502

    response = client.get(f"/session/{code}")
    assert response.json()["status"] == "waiting"
