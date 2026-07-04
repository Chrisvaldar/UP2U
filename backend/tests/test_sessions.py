import pytest
from fastapi.testclient import TestClient

import json
from app.main import app
from app import redis_client
from app import config
from app import errors
from app.services import places
from app.services import ai_reveal
from app.services import photos
from app.services import geocoding

client = TestClient(app)


def test_health():
    """Assert GET / returns 200 and the liveness message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "It's alive!"}


def test_create_session():
    """Assert POST /create-session returns a six-character uppercase alphanumeric code."""
    response = client.post("/create-session", json={"host_name": "test"})
    assert response.status_code == 200
    data = response.json()
    code = data["code"]
    assert len(code) == 6
    assert all(char.isdigit() or char.isupper() for char in code)


def test_get_session():
    """Assert GET /session/{code} returns the created session with waiting status."""
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
    """Assert GET /session/{code} returns 404 for an unknown code."""
    response = client.get("/session/696969")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_join_session():
    """Assert POST /join-session/{code} adds a participant visible in GET /session/{code}."""
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
    """Assert POST /join-session/{code} returns 404 for an unknown session."""
    response = client.post("/join-session/696969", json={"participant_name": "test"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_join_session_conflict_revealing(fake_redis):
    """
    Assert join is rejected with 409 when session status is revealing.

    Args:
        fake_redis: In-memory Redis fixture with a pre-seeded revealing session.
    """
    code = "ABC123"
    session = {
        "code": code,
        "host": "test",
        "status": "revealing",
        "location": None,
        "participants": ["test"],
        "answers": {},
    }
    fake_redis.set(redis_client.session_key(code), json.dumps(session), ex=3600)

    response = client.post(
        f"/join-session/{code}", json={"participant_name": "latecomer"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Uh oh! The group has decided already :("


def test_join_session_conflict_reveal_failed(fake_redis):
    """
    Assert join is rejected with 409 when session status is reveal_failed.

    Args:
        fake_redis: In-memory Redis fixture with a pre-seeded reveal_failed session.
    """
    code = "ABC123"
    session = {
        "code": code,
        "host": "test",
        "status": "reveal_failed",
        "location": None,
        "participants": ["test"],
        "answers": {},
    }
    fake_redis.set(redis_client.session_key(code), json.dumps(session), ex=3600)

    response = client.post(
        f"/join-session/{code}", json={"participant_name": "latecomer"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Uh oh! The group has decided already :("


def test_end_session():
    """Assert host can end a session and subsequent GET returns 404."""
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    end_response = client.post(f"/end-session/{code}", json={"host_name": "test"})
    assert end_response.status_code == 200

    response = client.get(f"/session/{code}")
    assert response.status_code == 404


def test_end_session_not_host():
    """Assert non-host POST /end-session/{code} returns 403 and session remains."""
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    end_response = client.post(f"/end-session/{code}", json={"host_name": "test2"})
    assert end_response.status_code == 403

    response = client.get(f"/session/{code}")
    assert response.status_code == 200


def test_end_session_not_found():
    """Assert POST /end-session/{code} returns 404 for an unknown session."""
    response = client.post(f"/end-session/696969", json={"host_name": "test"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_ttl_preserved_on_join(fake_redis):
    """
    Assert joining a participant does not materially extend the session TTL.

    Args:
        fake_redis: In-memory Redis fixture used to read TTL before and after join.
    """
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    ttl_before = fake_redis.ttl(redis_client.session_key(code))

    client.post(f"/join-session/{code}", json={"participant_name": "test2"})

    ttl_after = fake_redis.ttl(redis_client.session_key(code))

    assert ttl_before - ttl_after < 5


def test_start_session(monkeypatch):
    """
    Assert host start sets active status and stores mocked cuisines.

    Args:
        monkeypatch: Pytest fixture used to stub places.location_to_cuisines.
    """
    monkeypatch.setattr(
        places, "location_to_cuisines", lambda lat, lng: ["thai", "italian"]
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
    """Assert non-host POST /start-session/{code} returns 403."""
    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    start_response = client.post(
        f"/start-session/{code}", json={"host_name": "test2", "lat": 0, "lng": 0}
    )
    assert start_response.status_code == 403
    assert start_response.json()["detail"] == "Only the host can start the session."


def test_start_session_not_found():
    """Assert POST /start-session/{code} returns 404 for an unknown session."""
    response = client.post(
        f"/start-session/696969", json={"host_name": "test", "lat": 0, "lng": 0}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_start_session_places_failure(monkeypatch):
    """
    Assert upstream cuisine failure returns 502 and leaves session waiting.

    Args:
        monkeypatch: Pytest fixture used to make location_to_cuisines raise UpstreamBadResponse.
    """
    def raise_bad_response(lat, lng):
        raise errors.UpstreamBadResponse("places failed")

    monkeypatch.setattr(places, "location_to_cuisines", raise_bad_response)

    create_response = client.post("/create-session", json={"host_name": "test"})
    code = create_response.json()["code"]

    start_response = client.post(
        f"/start-session/{code}", json={"host_name": "test", "lat": 0, "lng": 0}
    )
    assert start_response.status_code == 502

    response = client.get(f"/session/{code}")
    assert response.json()["status"] == "waiting"


def test_submit_answers_single(fake_redis):
    """
    Assert a partial answer submission keeps session status active.

    Args:
        fake_redis: In-memory Redis fixture with a two-participant active session.
    """
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
    fake_redis.set(redis_client.session_key(code), json.dumps(session), ex=3600)

    submit_response = client.post(
        f"/submit-answers/{code}",
        json={"participant_name": "host", "answers": {}},
    )
    assert submit_response.status_code == 200

    response = client.get(f"/session/{code}")
    assert response.json()["status"] == "active"


def test_submit_answers_participant_not_found():
    """Assert submit answers returns 404 when participant is not in the session."""
    create_response = client.post("/create-session", json={"host_name": "host"})
    code = create_response.json()["code"]

    submit_response = client.post(
        f"/submit-answers/{code}",
        json={"participant_name": "not host", "answers": {}},
    )
    assert submit_response.status_code == 404
    assert submit_response.json()["detail"] == "Participant not found"


def test_submit_answers_triggers_reveal(monkeypatch, fake_redis):
    """
    Assert final answer submission runs reveal and sets status to revealed.

    Args:
        monkeypatch: Pytest fixture used to stub ai_reveal.run_reveal_pipeline.
        fake_redis: In-memory Redis fixture with a two-participant active session.
    """
    fake_reveal = {
        "primary": {"name": "Test Restaurant", "reason": "...", "maps_link": "..."},
        "backups": [],
        "personality_lines": {},
        "agreements": "",
        "conflicts": "",
    }
    monkeypatch.setattr(
        ai_reveal, "run_reveal_pipeline", lambda users, lat, lng: fake_reveal
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
    fake_redis.set(redis_client.session_key(code), json.dumps(session), ex=3600)

    client.post(
        f"/submit-answers/{code}", json={"participant_name": "host", "answers": {}}
    )
    submit_response = client.post(
        f"/submit-answers/{code}", json={"participant_name": "friend", "answers": {}}
    )

    assert submit_response.status_code == 200
    response = client.get(f"/session/{code}")
    assert response.json()["status"] == "revealed"
    assert response.json()["reveal"] == fake_reveal


def test_submit_answers_reveal_failed(monkeypatch, fake_redis):
    """
    Assert reveal pipeline failure sets status reveal_failed while returning 200.

    Args:
        monkeypatch: Pytest fixture used to make run_reveal_pipeline raise UpstreamBadResponse.
        fake_redis: In-memory Redis fixture with a two-participant active session.
    """
    def raise_bad_response(users, lat, lng):
        raise errors.UpstreamBadResponse("places failed")

    monkeypatch.setattr(ai_reveal, "run_reveal_pipeline", raise_bad_response)

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
    fake_redis.set(redis_client.session_key(code), json.dumps(session), ex=3600)

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
    """
    Assert host retry clears answers and resets reveal_failed to active.

    Args:
        fake_redis: In-memory Redis fixture with a reveal_failed session.
    """
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
    fake_redis.set(redis_client.session_key(code), json.dumps(session), ex=3600)

    retry_response = client.post(f"/retry-session/{code}", json={"host_name": "host"})
    assert retry_response.status_code == 200

    response = client.get(f"/session/{code}")
    data = response.json()
    assert data["status"] == "active"
    assert data["answers"] == {}

def test_retry_session_wrong_status(fake_redis):
    """
    Assert retry returns 409 when session status is not reveal_failed.

    Args:
        fake_redis: In-memory Redis fixture with a revealing session.
    """
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
    fake_redis.set(redis_client.session_key(code), json.dumps(session), ex=3600)

    retry_response = client.post(f"/retry-session/{code}", json={"host_name": "host"})
    assert retry_response.status_code == 409
    assert retry_response.json()["detail"] == "Retry is only available if pipeline fails"

def test_retry_session_not_host(fake_redis):
    """
    Assert non-host retry returns 403.

    Args:
        fake_redis: In-memory Redis fixture with a reveal_failed session.
    """
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
    fake_redis.set(redis_client.session_key(code), json.dumps(session), ex=3600)

    retry_response = client.post(f"/retry-session/{code}", json={"host_name": "friend"})
    assert retry_response.status_code == 403
    assert retry_response.json()["detail"] == "Only the host can retry the session."

def test_debug_routes_disabled(monkeypatch):
    """
    Assert dev endpoints return 404 when DEBUG is False.

    Args:
        monkeypatch: Pytest fixture used to set config.DEBUG to False.
    """
    monkeypatch.setattr(config, "DEBUG", False)

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
    """
    Assert dev endpoints return 200 when DEBUG is True and dependencies are stubbed.

    Args:
        monkeypatch: Pytest fixture used to enable DEBUG and stub service calls.
    """
    monkeypatch.setattr(config, "DEBUG", True)
    monkeypatch.setattr(places, "get_nearby_restaurants", lambda lat, lng, radius: [])
    monkeypatch.setattr(ai_reveal, "run_reveal_pipeline", lambda users, lat, lng: {"primary": {}, "backups": []})
    monkeypatch.setattr(geocoding, "geocode_location", lambda address: (0.0, 0.0))

    places_response = client.get("/test-places")
    assert places_response.status_code == 200

    reveal_response = client.get("/test-reveal")
    assert reveal_response.status_code == 200

    geocode_response = client.get("/test-geocode")
    assert geocode_response.status_code == 200

def test_photo_not_found(monkeypatch):
    """
    Assert GET /photo/{place_id}/{index} returns 404 when no photos exist.

    Args:
        monkeypatch: Pytest fixture used to make get_photo_names return None.
    """
    monkeypatch.setattr(photos, "get_photo_names", lambda place_id, strict: None)

    photos_response = client.get("/photo/696969/0")
    assert photos_response.status_code == 404

def test_photo_upstream_error(monkeypatch):
    """
    Assert photo upstream timeout maps to HTTP 504.

    Args:
        monkeypatch: Pytest fixture used to make get_photo_names raise UpstreamTimeout.
    """
    def raise_timeout(place_id, strict):
        raise errors.UpstreamTimeout("photo names timed out")

    monkeypatch.setattr(photos, "get_photo_names", raise_timeout)

    response = client.get("/photo/696969/0")
    assert response.status_code == 504

def test_ws_connect():
    """Assert a WebSocket client can connect to /ws/{code}/{name} without error."""
    with client.websocket_connect("/ws/ABC123/Chris") as ws:
        pass

def test_join_broadcasts_participant_joined():
    """Assert join_session broadcasts participant_joined to connected WebSocket clients."""
    create_response = client.post("/create-session", json={"host_name": "host"})
    code = create_response.json()["code"]

    with client.websocket_connect(f"/ws/{code}/host") as ws:
        client.post(f"/join-session/{code}", json={"participant_name": "friend"})

        message = ws.receive_json()
        assert message["type"] == "participant_joined"
        assert message["data"]["name"] == "friend"
