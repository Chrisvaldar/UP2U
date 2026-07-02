import pytest
from fastapi.testclient import TestClient

from main import app

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
    response = client.get(f"/session/696969")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"