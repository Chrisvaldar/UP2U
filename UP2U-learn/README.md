# UP2U Learn

UP2U Learn is the canonical version of UP2U: a real-time group dining decision app. The original `../backend` and `../frontend` directories are reference-only during consolidation.

## Current Architecture

- `frontend/`: React 19, Vite 8, TypeScript, Tailwind 4, React Router, Axios, Google Maps Places autocomplete, dnd-kit ranking UI, Embla reveal carousel.
- `backend/`: FastAPI, Redis session storage, WebSockets, Google Places, Gemini reveal generation, optional Groq fallback.
- Redis stores session state with a one-hour TTL.
- WebSockets broadcast lobby, survey, and reveal events to every connected client in the session.

## Local Setup

Backend:

```powershell
cd UP2U-learn\backend
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```powershell
cd UP2U-learn\frontend
npm install
npm.cmd run dev
```

Redis:

```powershell
docker run -d -p 6379:6379 redis
```

Backend env vars:

```text
REDIS_URL=redis://localhost:6379
GOOGLE_PLACES_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
```

Frontend env vars:

```text
VITE_GOOGLE_MAPS_API_KEY=
```

## Backend API

- `GET /`: health check.
- `POST /create-session`: creates a session and returns `{ "code": "ABC123" }`.
- `GET /session/{code}`: returns session JSON or `{ "error": "session not found" }`.
- `POST /join-session/{code}`: adds a participant and broadcasts `participant_joined`.
- `POST /start-session/{code}`: host-only start using `host_name`, `lat`, and `lng`; broadcasts `session_started`.
- `POST /submit-answers/{code}`: stores answers, broadcasts `answer_submitted`, and broadcasts `reveal_ready` when everyone has submitted.
- `GET /test-places`: Places smoke test.
- `GET /test-reveal`: full reveal smoke test with hardcoded sample users.
- `GET /test-geocode`: geocoding smoke test.
- `WS /ws/{session_code}/{participant_name}`: live session event stream.

## WebSocket Events

- `participant_joined`: `{ name, participants }`
- `session_started`: `{ host, lat, lng, participants }`
- `answer_submitted`: `{ name, submitted, total }`
- `reveal_ready`: full reveal payload with personality lines, agreements, conflicts, primary restaurant, and backups.

## Frontend Pages

- `/`: create or join a session with validation, loading state, and error handling.
- `/lobby/:code`: shows participants, lets the host choose a Google Places location, and starts the session.
- `/survey/:code`: collects hunger, vibe, ranked cuisines, travel distance, and dietary requirements.
- `/reveal/:code`: displays the live reveal payload from the WebSocket event.

## Verification

```powershell
cd UP2U-learn\frontend
npm.cmd run build

cd ..\backend
venv\Scripts\python.exe -m pytest
```

Backend tests are currently skipped placeholders from the learning phase. They document intended smoke coverage but do not yet assert behavior.

## Known Limitations

- API and WebSocket URLs are hardcoded to `127.0.0.1:8000`.
- Refreshing `/reveal/:code` loses the in-memory reveal payload.
- WebSocket connections are in-memory and are not multi-instance safe.
- Dev/test endpoints should be removed or protected before production.
- Backend tests need to be replaced with real assertions.
