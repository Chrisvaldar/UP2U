"""
UP2U Learn — Backend
====================
Rebuild the UP2U backend yourself. Reference: ../../backend/main.py

Day 1 goals:
  - GET  /                  health check
  - POST /create-session    6-char code, store in Redis (1h TTL)
  - GET  /session/{code}    return session JSON or error

Run:
  uvicorn main:app --reload

Docs:
  http://localhost:8000/docs
"""

import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import redis
import random
import string
import json

load_dotenv()
r = redis.Redis.from_url(os.getenv("REDIS_URL"))

app = FastAPI(title="UP2U Learn")


class CreateSessionRequest(BaseModel):
    host_name: str


class JoinSessionRequest(BaseModel):
    participant_name: str


class StartSessionRequest(BaseModel):
    host_name: str
    location: str


def session_key(code: str) -> str:
    return f"session:{code}"


@app.get("/")
def health():
    return {"message": "It's alive!"}


@app.post("/create-session")
def create_session(request: CreateSessionRequest):
    ttl_seconds = 3600

    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    session = {
        "code": code,
        "host": request.host_name,
        "status": "waiting",
        "location": None,
        "participants": [],
        "answers": {},
    }

    r.setex(session_key(code), ttl_seconds, json.dumps(session))

    return {"code": code}


@app.get("/session/{code}")
def get_session(code: str):
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}
    return json.loads(data)


@app.post("/join-session/{code}")
def join_session(request: JoinSessionRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}

    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))

    session["participants"].append(request.participant_name)
    r.setex(session_key(code), ttl_seconds, json.dumps(session))

    return session


@app.post("/start-session/{code}")
def start_session(request: StartSessionRequest, code: str):
    data = r.get(session_key(code))
    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))

    if request.host_name == session["host"]:
        session["status"] = "active"
        session["location"] = request.location

        r.setex(session_key(code), ttl_seconds, json.dumps(session))
        return session

    return {"error": "Only the host can start the session"}


# TODO (Day 1): Add Pydantic models and Redis connection
# TODO (Day 1): POST /create-session
# TODO (Day 1): GET /session/{code}
# TODO (Day 2): POST /join-session/{code}
# TODO (Day 2): POST /start-session/{code}
# TODO (Day 2): POST /submit-answers/{code}
# TODO (Day 3): ConnectionManager + WebSocket /ws/{code}/{name}
# TODO (Day 4): Places API + Gemini reveal pipeline
