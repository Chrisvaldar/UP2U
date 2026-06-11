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

    r.setex(f"session:{code}", ttl_seconds, json.dumps(session))

    return {"code": code}


@app.get("/session/{code}")
def get_session():
    data = r.get(request.code)
    if data is None:
      return {"error": "session not found"}
    return json.loads(data)


# TODO (Day 1): Add Pydantic models and Redis connection
# TODO (Day 1): POST /create-session
# TODO (Day 1): GET /session/{code}
# TODO (Day 2): POST /join-session/{code}
# TODO (Day 2): POST /start-session/{code}
# TODO (Day 2): POST /submit-answers/{code}
# TODO (Day 3): ConnectionManager + WebSocket /ws/{code}/{name}
# TODO (Day 4): Places API + Gemini reveal pipeline
