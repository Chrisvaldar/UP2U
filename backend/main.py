from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
import os
import redis
import random, string
import json
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

r = redis.Redis.from_url(os.getenv("REDIS_URL"))

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    host_name: str


class JoinSessionRequest(BaseModel):
    participant_name: str


class StartSessionRequest(BaseModel):
    host_name: str
    location: str


class SubmitAnswersRequest(BaseModel):
    participant_name: str
    answer: str


class ConnectionManager:
    def __init__(self):
        # stores connections grouped by session code
        # {"ABC123": [websocket1, websocket2, websocket3]}
        self.sessions = {}

    async def connect(self, session_code: str, websocket: WebSocket):
        # add this websocket to the session's list
        await websocket.accept()
        if session_code not in self.sessions:
            self.sessions[session_code] = []
        self.sessions[session_code].append(websocket)

    async def disconnect(self, session_code: str, websocket: WebSocket):
        # remove this websocket from the session's list
        self.sessions[session_code].remove(websocket)

    async def broadcast(self, session_code: str, event: dict):
        # send message to every websocket in the session
        for ws in self.sessions[session_code]:
            await ws.send_text(json.dumps(event))


manager = ConnectionManager()


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
async def join_session(code: str, request: JoinSessionRequest):
    key = f"session:{code}"
    ttl = r.ttl(key)
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    dict_data = json.loads(data)
    dict_data["participants"].append(request.participant_name)

    r.setex(key, ttl, json.dumps(dict_data))

    await manager.broadcast(
        code,
        {
            "type": "participant_joined",
            "data": {
                "name": request.participant_name,
                "participants": dict_data["participants"],
            },
        },
    )

    return {"session_code": code}


@app.post("/start-session/{code}")
async def start_session(code: str, request: StartSessionRequest):
    key = f"session:{code}"
    ttl = r.ttl(key)
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    dict_data = json.loads(data)

    if request.host_name != dict_data["host"]:
        return "Only the host can start the session"

    dict_data["status"] = "active"
    dict_data["location"] = request.location

    r.setex(key, ttl, json.dumps(dict_data))

    await manager.broadcast(
        code, {"type": "session_started", "data": {"location": request.location}}
    )

    return dict_data


@app.post("/submit-answers/{code}")
async def submit_answers(code: str, request: SubmitAnswersRequest):
    key = f"session:{code}"
    ttl = r.ttl(key)
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    dict_data = json.loads(data)

    if request.participant_name not in dict_data["participants"]:
        return "Participant name not found in session"

    dict_data["answers"][request.participant_name] = request.answer

    if len(dict_data["answers"]) == len(dict_data["participants"]):
        # everyone has submitted
        dict_data["status"] = "revealing"
        # trigger AI + Places API call

    r.setex(key, ttl, json.dumps(dict_data))

    await manager.broadcast(
        code,
        {
            "type": "answer_submitted",
            "data": {
                "name": request.participant_name,
                "submitted": list(dict_data["answers"].keys()),
                "total": len(dict_data["participants"]),
            },
        },
    )

    # and if everyone submitted:
    if len(dict_data["answers"]) == len(dict_data["participants"]):
        await manager.broadcast(code, {"type": "all_submitted", "data": {}})

    return dict_data


@app.websocket("/ws/{session_code}/{participant_name}")
async def websocket_endpoint(
    websocket: WebSocket, session_code: str, participant_name: str
):
    await manager.connect(session_code, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # for now just broadcast whatever message we receive to everyone
            await manager.broadcast(session_code, f"{participant_name}: {data}")
    except Exception:
        await manager.disconnect(session_code, websocket)
