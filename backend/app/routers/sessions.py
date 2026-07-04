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
    """Return a simple liveness check for the API."""
    return {"message": "It's alive!"}


@router.post("/create-session")
def create_session(request: models.CreateSessionRequest):
    """
    Create a new session with a random six-character code.

    Stores the session in Redis with a one-hour TTL and the host as the first
    participant.

    Args:
        request: CreateSessionRequest with host_name.

    Returns:
        Dict containing the new session code.
    """
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
    """
    Fetch the current session state from Redis.

    Args:
        code: Six-character session code.

    Returns:
        Session dict with host, status, participants, answers, and location fields.

    Raises:
        HTTPException: 404 when no session exists for the code.
    """
    data = redis_client.r.get(redis_client.session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return json.loads(data)


@router.post("/join-session/{code}")
async def join_session(request: models.JoinSessionRequest, code: str):
    """
    Add a participant to a session and broadcast participant_joined.

    Preserves the existing Redis TTL so joins do not extend session lifetime.

    Args:
        request: JoinSessionRequest with participant_name.
        code: Six-character session code.

    Returns:
        Updated session dict including the new participant.

    Raises:
        HTTPException: 404 when the session is not found.
        HTTPException: 409 when the session is revealing, reveal_failed, or revealed.
    """
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
    """
    Host-only endpoint to set location, fetch cuisines, and activate the session.

    Broadcasts session_started with lat, lng, participants, and cuisine options.

    Args:
        request: StartSessionRequest with host_name, lat, and lng.
        code: Six-character session code.

    Returns:
        Updated session dict with status active and cuisines list.

    Raises:
        HTTPException: 404 when the session is not found.
        HTTPException: 403 when the caller is not the host.
        HTTPException: 502/503/504 when cuisine discovery fails upstream.
    """
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
    """
    Host-only endpoint to reset a reveal_failed session back to active.

    Clears stored answers and broadcasts a retrying event.

    Args:
        code: Six-character session code.
        request: RetrySessionRequest with host_name.

    Returns:
        Updated session dict with status active and empty answers.

    Raises:
        HTTPException: 404 when the session is not found.
        HTTPException: 403 when the caller is not the host.
        HTTPException: 409 when status is not reveal_failed.
    """
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
    """
    Host-only endpoint to end a session and delete it from Redis.

    Broadcasts session_ended before removing the session key.

    Args:
        code: Six-character session code.
        request: EndSessionRequest with host_name.

    Returns:
        Final session dict before deletion.

    Raises:
        HTTPException: 404 when the session is not found.
        HTTPException: 403 when the caller is not the host.
    """
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
