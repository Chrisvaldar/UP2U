import json
from fastapi import APIRouter, WebSocket

router = APIRouter()


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


@router.websocket("/ws/{session_code}/{participant_name}")
async def websocket_endpoint(
    websocket: WebSocket, session_code: str, participant_name: str
):
    await manager.connect(session_code, websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        # Drop the socket from the session pool when the client disconnects or the loop exits.
        await manager.disconnect(session_code, websocket)
