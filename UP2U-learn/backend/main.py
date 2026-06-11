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

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="UP2U Learn")
class CreateSessionRequest(BaseModel):
  host_name: str

@app.get("/")
def health():
    return {"message": "It's alive!"}

@app.post("/create-session")
def create_session(request: CreateSessionRequest):
    return {"message": f"ur name is {request.host_name}"}

# TODO (Day 1): Add Pydantic models and Redis connection
# TODO (Day 1): POST /create-session
# TODO (Day 1): GET /session/{code}
# TODO (Day 2): POST /join-session/{code}
# TODO (Day 2): POST /start-session/{code}
# TODO (Day 2): POST /submit-answers/{code}
# TODO (Day 3): ConnectionManager + WebSocket /ws/{code}/{name}
# TODO (Day 4): Places API + Gemini reveal pipeline
