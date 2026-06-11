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
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from dotenv import load_dotenv
import redis
import random
import string
import json

load_dotenv()
r = redis.Redis.from_url(os.getenv("REDIS_URL"))

app = FastAPI(title="UP2U Learn")


class ConnectionManager:
    def __init__(self):
        self.sessions: dict[str, list[WebSocket]] = {}

    async def connect(self, session_code: str, websocket: WebSocket):
        await websocket.accept()
        if session_code not in self.sessions:
            self.sessions[session_code] = []
        self.sessions[session_code].append(websocket)

    async def disconnect(self, session_code: str, websocket: WebSocket):
        self.sessions[session_code].remove(websocket)

    async def broadcast(self, session_code: str, event: dict):
        if session_code not in self.sessions:
            return
        for ws in self.sessions[session_code]:
            await ws.send_text(json.dumps(event))


manager = ConnectionManager()


class CreateSessionRequest(BaseModel):
    host_name: str


class JoinSessionRequest(BaseModel):
    participant_name: str


class StartSessionRequest(BaseModel):
    host_name: str
    location: str


class SubmitAnswersRequest(BaseModel):
    participant_name: str
    answers: dict


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
async def join_session(request: JoinSessionRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}

    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))

    session["participants"].append(request.participant_name)
    r.setex(session_key(code), ttl_seconds, json.dumps(session))

    await manager.broadcast(
        code,
        {
            "type": "participant_joined",
            "data": {
                "name": request.participant_name,
                "participants": session["participants"],
            },
        },
    )

    return session


@app.post("/start-session/{code}")
async def start_session(request: StartSessionRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}
    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))

    if request.host_name == session["host"]:
        session["status"] = "active"
        session["location"] = request.location

        r.setex(session_key(code), ttl_seconds, json.dumps(session))
        await manager.broadcast(
            code,
            {
                "type": "session_started",
                "data": {
                    "host": request.host_name,
                    "location": request.location,
                    "participants": session["participants"],
                },
            },
        )
        return session

    return {"error": "Only the host can start the session"}


@app.post("/submit-answers/{code}")
async def submit_answers(request: SubmitAnswersRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}

    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))

    if request.participant_name not in session["participants"]:
        return {"error": "Participant not found"}
    session["answers"][request.participant_name] = request.answers

    await manager.broadcast(
        code,
        {
            "type": "answer_submitted",
            "data": {
                "name": request.participant_name,
                "submitted": list(session["answers"].keys()),
                "total": len(session["participants"]),
            },
        },
    )

    if len(session["answers"]) == len(session["participants"]):
        session["status"] = "revealing"
        reveal = {"placeholder": "todo"}  # temp until Gemini
        await manager.broadcast(code, {"type": "reveal_ready", "data": reveal})

    r.setex(session_key(code), ttl_seconds, json.dumps(session))
    return session


@app.websocket("/ws/{session_code}/{participant_name}")
async def websocket_endpoint(
    websocket: WebSocket, session_code: str, participant_name: str
):
    await manager.connect(session_code, websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        await manager.disconnect(session_code, websocket)


# TODO (Day 3): ConnectionManager + WebSocket /ws/{code}/{name}
# TODO (Day 4): Places API + Gemini reveal pipeline
