import asyncio
import json

from fastapi import APIRouter, HTTPException, Request

from app import config
from app import errors
from app import models
from app import redis_client
from app import ws
from app.limiter import limiter
from app.services import ai_reveal

router = APIRouter()


@router.post("/submit-answers/{code}")
@limiter.limit("5/minute")
async def submit_answers(request: Request, code: str, body: models.SubmitAnswersRequest):
    """
    Store a participant's survey answers and trigger reveal when all have submitted.

    Broadcasts answer_submitted on each submission. When every participant has
    answered, runs the reveal pipeline in a thread and broadcasts reveal_ready
    or reveal_failed.

    Args:
        body: Participant name and survey answer payload.
        code: Six-character session code.

    Returns:
        Updated session dict including answers and status.

    Raises:
        HTTPException: 404 if the session or participant is not found.
    """
    data = redis_client.r.get(redis_client.session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = json.loads(data)
    # Preserve the original expiry so normal activity does not extend a session.
    ttl_seconds = redis_client.r.ttl(redis_client.session_key(code))

    if body.participant_name not in session["participants"]:
        raise HTTPException(status_code=404, detail="Participant not found")
    session["answers"][body.participant_name] = body.answers

    await ws.manager.broadcast(
        code,
        {
            "type": "answer_submitted",
            "data": {
                "name": body.participant_name,
                "submitted": list(session["answers"].keys()),
                "total": len(session["participants"]),
            },
        },
    )

    if len(session["answers"]) == len(session["participants"]):
        session["status"] = "revealing"
        redis_client.r.set(redis_client.session_key(code), json.dumps(session), ex=ttl_seconds)
        lat = session["lat"]
        lng = session["lng"]
        users = [{"name": name, **ans} for name, ans in session["answers"].items()]
        try:
            # The reveal pipeline performs blocking HTTP/AI calls; keep the event loop responsive.
            reveal = await asyncio.to_thread(ai_reveal.run_reveal_pipeline, users, lat, lng)
            session["status"] = "revealed"
            session["reveal"] = reveal
            await ws.manager.broadcast(code, {"type": "reveal_ready", "data": reveal})
            config.logger.info(
                f"Reveal succeeded for {code} → primary: {reveal['primary']['name']}, backups: {[b['name'] for b in reveal['backups']]}"
            )
        except errors.UpstreamError as e:
            session["status"] = "reveal_failed"
            redis_client.r.set(redis_client.session_key(code), json.dumps(session), ex=ttl_seconds)
            config.logger.error(
                f"Reveal pipeline failed for session {code}: {type(e).__name__}: {e}"
            )
            await ws.manager.broadcast(
                code,
                {"type": "reveal_failed", "data": {"error": "Oops! Reveal failed"}},
            )
        except Exception:
            session["status"] = "reveal_failed"
            redis_client.r.set(redis_client.session_key(code), json.dumps(session), ex=ttl_seconds)
            config.logger.exception(f"Reveal pipeline failed for session {code}")
            await ws.manager.broadcast(
                code,
                {"type": "reveal_failed", "data": {"error": "Oops! Reveal failed"}},
            )
    redis_client.r.set(redis_client.session_key(code), json.dumps(session), ex=ttl_seconds)
    return session
