import json
import random
import string

from fastapi import APIRouter, HTTPException

from app import config
from app import errors
from app import models
from app import redis_client
from app import ws
from app.services import places

router = APIRouter()


@router.get("/")
def health():
    return {"message": "It's alive!"}


@router.post("/create-session")
def create_session(request: models.CreateSessionRequest):
    ttl_seconds = 3600

    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    session = {
        "code": code,
        "host": request.host_name,
        "status": "waiting",
        "location": None,
        "participants": [request.host_name],
        "answers": {},
    }

    redis_client.r.set(redis_client.session_key(code), json.dumps(session), ex=ttl_seconds)
    config.logger.info(f"Session {code} created by {request.host_name}")
    return {"code": code}


@router.get("/session/{code}")
def get_session(code: str):
    data = redis_client.r.get(redis_client.session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return json.loads(data)


@router.post("/join-session/{code}")
async def join_session(request: models.JoinSessionRequest, code: str):
    data = redis_client.r.get(redis_client.session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = json.loads(data)
    # Preserve the original expiry so normal activity does not extend a session.
    ttl_seconds = redis_client.r.ttl(redis_client.session_key(code))

    if (
        session["status"] == "revealing"
        or session["status"] == "reveal_failed"
        or session["status"] == "revealed"
    ):
        config.logger.warning(
            f"Join rejected for {code}: session status is {session['status']}"
        )
        raise HTTPException(
            status_code=409, detail="Uh oh! The group has decided already :("
        )
    session["participants"].append(request.participant_name)
    redis_client.r.set(redis_client.session_key(code), json.dumps(session), ex=ttl_seconds)

    await ws.manager.broadcast(
        code,
        {
            "type": "participant_joined",
            "data": {
                "name": request.participant_name,
                "participants": session["participants"],
            },
        },
    )
    config.logger.info(f"{request.participant_name} joined session {code}")
    return session


@router.post("/start-session/{code}")
async def start_session(request: models.StartSessionRequest, code: str):
    data = redis_client.r.get(redis_client.session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session = json.loads(data)
    ttl_seconds = redis_client.r.ttl(redis_client.session_key(code))

    if request.host_name == session["host"]:
        session["status"] = "active"
        session["lat"] = request.lat
        session["lng"] = request.lng
        try:
            cuisines = places.location_to_cuisines(session["lat"], session["lng"])
        except errors.UpstreamError as e:
            raise errors.upstream_to_http(e)
        session["cuisines"] = cuisines

        # Preserve the original expiry so normal activity does not extend a session.
        redis_client.r.set(redis_client.session_key(code), json.dumps(session), ex=ttl_seconds)
        await ws.manager.broadcast(
            code,
            {
                "type": "session_started",
                "data": {
                    "host": request.host_name,
                    "lat": request.lat,
                    "lng": request.lng,
                    "participants": session["participants"],
                    "cuisines": cuisines,
                },
            },
        )
        config.logger.info(
            f"Session {code} started by {request.host_name} at ({request.lat}, {request.lng}) → cuisines: {cuisines}"
        )
        return session

    raise HTTPException(status_code=403, detail="Only the host can start the session.")


@router.post("/retry-session/{code}")
async def retry_session(code: str, request: models.RetrySessionRequest):
    data = redis_client.r.get(redis_client.session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = json.loads(data)
    ttl_seconds = redis_client.r.ttl(redis_client.session_key(code))
    if request.host_name == session["host"]:
        if session["status"] != "reveal_failed":
            raise HTTPException(
                status_code=409, detail="Retry is only available if pipeline fails"
            )

        session["status"] = "active"
        session["answers"] = {}
        redis_client.r.set(redis_client.session_key(code), json.dumps(session), ex=ttl_seconds)
        await ws.manager.broadcast(
            code, {"type": "retrying", "data": {"message": "attempting retry"}}
        )
        return session
    raise HTTPException(status_code=403, detail="Only the host can retry the session.")


@router.post("/end-session/{code}")
async def end_session(code: str, request: models.EndSessionRequest):
    data = redis_client.r.get(redis_client.session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = json.loads(data)
    if request.host_name == session["host"]:
        await ws.manager.broadcast(
            code, {"type": "session_ended", "data": {"message": "end of session"}}
        )

        redis_client.r.delete(redis_client.session_key(code))
        return session
    raise HTTPException(status_code=403, detail="Only the host can end the session.")
