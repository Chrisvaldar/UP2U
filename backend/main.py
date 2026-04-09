from fastapi import FastAPI
from dotenv import load_dotenv
import os
import redis
import random, string
import json

load_dotenv()

app = FastAPI()

r = redis.Redis.from_url(os.getenv("REDIS_URL"))

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    host_name: str


class JoinSessionRequest(BaseModel):
    participant_name: str


@app.get("/")
def root():
    return {"message": "UP2U backend is alive"}


@app.post("/create-session")
def create_session(request: CreateSessionRequest):
    new_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    key = f"session:{new_code}"
    session = {
        "code": new_code,
        "host": request.host_name,
        "status": "waiting",
        "location": None,
        "participants": [],
        "answers": {},
    }
    r.setex(key, 3600, json.dumps(session))

    return {"session_code": new_code}


@app.get("/session/{code}")
def get_session(code: str):
    key = f"session:{code}"
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    return json.loads(data)


@app.post("/join-session/{code}")
def join_session(code: str, request: JoinSessionRequest):
    key = f"session:{code}"
    ttl = r.ttl(key)
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    dict_data = json.loads(data)
    dict_data["participants"].append(request.participant_name)

    r.setex(key, 3600, json.dumps(dict_data))

    return {"session_code": code}
