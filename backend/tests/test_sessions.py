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

    start_response = client.post(
        f"/start-session/{code}", json={"host_name": "test", "lat": 0, "lng": 0}
    )
    assert start_response.status_code == 502

    response = client.get(f"/session/{code}")
    assert response.json()["status"] == "waiting"


def test_submit_answers_single(fake_redis):
    code = "ABC123"
    session = {
        "code": code,
        "host": "host",
        "status": "active",
        "location": None,
        "participants": ["host", "friend"],
        "answers": {},
        "lat": 0,
        "lng": 0,
    }
    fake_redis.set(main.session_key(code), json.dumps(session), ex=3600)

    submit_response = client.post(
        f"/submit-answers/{code}",
        json={"participant_name": "host", "answers": {}},
    )
    assert submit_response.status_code == 200

    response = client.get(f"/session/{code}")
    assert response.json()["status"] == "active"


def test_submit_answers_participant_not_found():
    create_response = client.post("/create-session", json={"host_name": "host"})
    code = create_response.json()["code"]

    submit_response = client.post(
        f"/submit-answers/{code}",
        json={"participant_name": "not host", "answers": {}},
    )
    assert submit_response.status_code == 404
    assert submit_response.json()["detail"] == "Participant not found"


def test_submit_answers_triggers_reveal(monkeypatch, fake_redis):
    fake_reveal = {
        "primary": {"name": "Test Restaurant", "reason": "...", "maps_link": "..."},
        "backups": [],
        "personality_lines": {},
        "agreements": "",
        "conflicts": "",
    }
    monkeypatch.setattr(
        main, "run_reveal_pipeline", lambda users, lat, lng: fake_reveal
    )

    code = "ABC123"
    session = {
        "code": code,
        "host": "host",
        "status": "active",
        "location": None,
        "participants": ["host", "friend"],
        "answers": {},
        "lat": 0,
        "lng": 0,
    }
    fake_redis.set(main.session_key(code), json.dumps(session), ex=3600)

    client.post(
        f"/submit-answers/{code}", json={"participant_name": "host", "answers": {}}
    )
    submit_response = client.post(
        f"/submit-answers/{code}", json={"participant_name": "friend", "answers": {}}
    )

    assert submit_response.status_code == 200
    response = client.get(f"/session/{code}")
    assert response.json()["status"] == "revealing"


def test_submit_answers_reveal_failed(monkeypatch, fake_redis):
    def raise_bad_response(users, lat, lng):
        raise main.UpstreamBadResponse("places failed")

    monkeypatch.setattr(main, "run_reveal_pipeline", raise_bad_response)

    code = "ABC123"
    session = {
        "code": code,
        "host": "host",
        "status": "active",
        "location": None,
        "participants": ["host", "friend"],
        "answers": {},
        "lat": 0,
        "lng": 0,
    }
    fake_redis.set(main.session_key(code), json.dumps(session), ex=3600)

    client.post(
        f"/submit-answers/{code}", json={"participant_name": "host", "answers": {}}
    )
    submit_response = client.post(
        f"/submit-answers/{code}", json={"participant_name": "friend", "answers": {}}
    )

    # Intentional: answers already persisted, 
    # so this stays 200 even on reveal failure -> see session["status"] / WS for the real outcome
    assert submit_response.status_code == 200
    response = client.get(f"/session/{code}")
    assert response.json()["status"] == "reveal_failed"

def test_retry_session(fake_redis):
    code = "ABC123"
    session = {
        "code": code,
        "host": "host",
        "status": "reveal_failed",
        "location": None,
        "participants": ["host", "friend"],
        "answers": {"host": {"hunger": 3}, "friend": {"hunger": 5}},
        "lat": 0,
        "lng": 0,
    }
    fake_redis.set(main.session_key(code), json.dumps(session), ex=3600)

    retry_response = client.post(f"/retry-session/{code}", json={"host_name": "host"})
    assert retry_response.status_code == 200

    response = client.get(f"/session/{code}")
    data = response.json()
    assert data["status"] == "active"
    assert data["answers"] == {}

def test_retry_session_wrong_status(fake_redis):
    code = "ABC123"
    session = {
        "code": code,
        "host": "host",
        "status": "revealing",
        "location": None,
        "participants": ["host", "friend"],
        "answers": {"host": {"hunger": 3}, "friend": {"hunger": 5}},
        "lat": 0,
        "lng": 0,
    }
    fake_redis.set(main.session_key(code), json.dumps(session), ex=3600)

    retry_response = client.post(f"/retry-session/{code}", json={"host_name": "host"})
    assert retry_response.status_code == 409
    assert retry_response.json()["detail"] == "Retry is only available if pipeline fails"

def test_retry_session_not_host(fake_redis):
    code = "ABC123"
    session = {
        "code": code,
        "host": "host",
        "status": "reveal_failed",
        "location": None,
        "participants": ["host", "friend"],
        "answers": {"host": {"hunger": 3}, "friend": {"hunger": 5}},
        "lat": 0,
        "lng": 0,
    }
    fake_redis.set(main.session_key(code), json.dumps(session), ex=3600)

    retry_response = client.post(f"/retry-session/{code}", json={"host_name": "friend"})
    assert retry_response.status_code == 403
    assert retry_response.json()["detail"] == "Only the host can retry the session."

def test_debug_routes_disabled(monkeypatch):
    monkeypatch.setattr(main, "DEBUG", False)

    test_places_response = client.get("/test-places")
    assert test_places_response.status_code == 404
    assert test_places_response.json()["detail"] == "Dev endpoint: Not found"

    test_reveal_response = client.get("/test-reveal")
    assert test_reveal_response.status_code == 404
    assert test_reveal_response.json()["detail"] == "Dev endpoint: Not found"

    test_geocode_response = client.get("/test-geocode")
    assert test_geocode_response.status_code == 404
    assert test_geocode_response.json()["detail"] == "Dev endpoint: Not found"

def test_debug_routes_enabled(monkeypatch):
    monkeypatch.setattr(main, "DEBUG", True)
    monkeypatch.setattr(main, "get_nearby_restaurants", lambda lat, lng, radius: [])
    monkeypatch.setattr(main, "run_reveal_pipeline", lambda users, lat, lng: {"primary": {}, "backups": []})
    monkeypatch.setattr(main, "geocode_location", lambda address: (0.0, 0.0))

    places_response = client.get("/test-places")
    assert places_response.status_code == 200

    reveal_response = client.get("/test-reveal")
    assert reveal_response.status_code == 200

    geocode_response = client.get("/test-geocode")
    assert geocode_response.status_code == 
    
