import json
from fastapi import APIRouter, WebSocket

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        """Initialize an empty map of session codes to WebSocket connections."""
        self.sessions: dict[str, list[WebSocket]] = {}

    async def connect(self, session_code: str, websocket: WebSocket):
        """
        Accept a WebSocket and register it for a session.

        Args:
            session_code: Session code identifying the connection pool.
            websocket: Incoming WebSocket connection to accept and track.
        """
        await websocket.accept()
        if session_code not in self.sessions:
            self.sessions[session_code] = []
        self.sessions[session_code].append(websocket)

    async def disconnect(self, session_code: str, websocket: WebSocket):
        """
        Remove a WebSocket from a session's connection pool.

        Args:
            session_code: Session code whose pool should be updated.
            websocket: WebSocket connection to remove.
        """
        self.sessions[session_code].remove(websocket)

    async def broadcast(self, session_code: str, event: dict):
        """
        Send a JSON event to all WebSockets connected to a session.

        Args:
            session_code: Session code whose subscribers receive the event.
            event: Dict serialized to JSON and sent to each connected client.
        """
        if session_code not in self.sessions:
            return
        for ws in self.sessions[session_code]:
            await ws.send_text(json.dumps(event))


manager = ConnectionManager()


@router.websocket("/ws/{session_code}/{participant_name}")
async def websocket_endpoint(
    websocket: WebSocket, session_code: str, participant_name: str
):
    """
    Keep a participant WebSocket alive until disconnect, then clean up the pool.

    Args:
        websocket: Client WebSocket connection.
        session_code: Session code from the URL path.
        participant_name: Participant name from the URL path (unused for routing).
    """
    await manager.connect(session_code, websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        # Drop the socket from the session pool when the client disconnects or the loop exits.
        await manager.disconnect(session_code, websocket)
