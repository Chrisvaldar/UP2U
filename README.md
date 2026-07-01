# UP2U

UP2U is a real-time group dining decision app: create a session, collect group preferences, and reveal a restaurant pick with AI-generated personality lines.

**Live app:** [https://up2u-app.vercel.app/](https://up2u-app.vercel.app/)

## Architecture

- `frontend/`: React 19, Vite 8, TypeScript, Tailwind 4, React Router, Axios, Google Maps Places autocomplete, dnd-kit ranking UI, Embla reveal carousel (outer restaurant slides + inner photo carousel per card). Hosted on **Vercel** (`frontend/` root).
- `backend/`: FastAPI, Redis session storage, WebSockets, Google Places, Gemini reveal generation, optional Groq fallback. Hosted on **Railway** (`backend/` root) with Railway **Redis**.
- Redis stores session state with a one-hour TTL.
- WebSockets broadcast lobby, survey, and reveal events to every connected client in the session.

## Production

| Service | URL |
|---------|-----|
| Frontend | [https://up2u-app.vercel.app/](https://up2u-app.vercel.app/) |
| Backend | `https://up2u-production.up.railway.app` |

**Vercel env vars:** `VITE_API_BASE` (Railway URL, **no trailing slash**), `VITE_GOOGLE_MAPS_API_KEY`

**Railway env vars:** `REDIS_URL` (reference from Redis service), `GOOGLE_PLACES_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY` (optional). Do not set `DEBUG` in production.

**CORS:** Backend allows `https://up2u-app.vercel.app` and local Vite dev origins only.

**Google Maps API keys (two keys recommended):**

| Key | File | Restrictions |
|-----|------|--------------|
| Browser | `frontend/.env` → `VITE_GOOGLE_MAPS_API_KEY` | Websites: Vercel + `http://localhost:5173/*` |
| Server | `backend/.env` → `GOOGLE_PLACES_API_KEY` | None today — restrict to Places Photo Media (+ other required APIs) before public launch; **restart uvicorn** after changing |

If `/test-places` returns 404, set `DEBUG=true`. If it returns `[]`, the backend key is wrong or uvicorn needs a restart.

## Local Setup

Backend:

```powershell
cd backend
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```powershell
cd frontend
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
DEBUG=true
```

Frontend env vars:

```text
VITE_GOOGLE_MAPS_API_KEY=
VITE_API_BASE=http://127.0.0.1:8000
```

(`VITE_API_BASE` optional locally — defaults to `http://127.0.0.1:8000`. Trailing slashes are stripped in `frontend/src/lib/config.ts`.)

## Backend API

Session business errors use FastAPI `HTTPException` — response body `{"detail": "<message>"}` with status **404** (not found), **403** (host-only), or **409** (state conflict). The frontend reads `err.response.data.detail` in axios catch blocks.

- `GET /`: health check.
- `POST /create-session`: creates a session and returns `{ "code": "ABC123" }`.
- `GET /session/{code}`: returns session JSON; **404** if missing.
- `POST /join-session/{code}`: adds a participant and broadcasts `participant_joined`; **404** if missing, **409** if session is `revealing` or `reveal_failed`.
- `POST /start-session/{code}`: host-only start using `host_name`, `lat`, and `lng`; broadcasts `session_started`; **403** if not host.
- `POST /submit-answers/{code}`: stores answers, broadcasts `answer_submitted`, runs reveal pipeline when everyone has submitted; broadcasts `reveal_ready` or `reveal_failed` (WebSocket); **404** if session or participant not found.
- `POST /retry-session/{code}`: host-only retry after `reveal_failed`; clears answers, broadcasts `retrying`; **403** / **409** as applicable.
- `POST /end-session/{code}`: host-only; broadcasts `session_ended`, deletes Redis session; **403** if not host.
- `GET /photo/{place_id}/{index}`: server-side photo proxy (streams Google Places Photo Media; keeps API key off the client).
- `GET /test-places`, `GET /test-reveal`, `GET /test-geocode`: dev smoke tests (require `DEBUG=true`; 404 otherwise).
- `WS /ws/{session_code}/{participant_name}`: live session event stream.

## WebSocket Events

- `participant_joined`: `{ name, participants }`
- `session_started`: `{ host, lat, lng, participants }`
- `answer_submitted`: `{ name, submitted, total }`
- `reveal_ready`: full reveal payload with personality lines, agreements, conflicts, primary restaurant, backups, and optional `photo_urls` per restaurant (served via `/photo/...` proxy).
- `reveal_failed`: `{ error }`
- `retrying`: `{ message }`
- `session_ended`: `{ message }`

## Frontend Pages

- `/`: create or join a session with validation, loading state, and error handling.
- `/lobby/:code`: shows participants, lets the host choose a Google Places location, and starts the session.
- `/survey/:code`: collects hunger, vibe, ranked cuisines, travel distance, and dietary requirements.
- `/reveal/:code`: personality slides, agreements/conflicts, restaurant carousel with photo carousels per card; reveal persisted in `sessionStorage`.

## Verification

```powershell
cd frontend
npm.cmd run build

cd ..\backend
venv\Scripts\python.exe -m pytest
```

Backend tests are currently skipped placeholders from the learning phase. They document intended smoke coverage but do not yet assert behavior.

## Known Limitations

- WebSocket connections are in-memory and are not multi-instance safe (single Railway instance is fine for friends beta).
- Reveal payload is in `sessionStorage` only — new tab or cleared storage loses reveal.
- Survey steps 0–4 reset on refresh (draft answers not persisted).
- `GOOGLE_PLACES_API_KEY` is server-side only (photo proxy), but the key has no API restrictions yet — restrict before public launch.
- Backend tests need to be replaced with real assertions.

Backend logs session lifecycle, reveal success/failure, Places errors, and AI JSON parse failures via Python `logging` (INFO level). See `PROJECT_HANDOFF.md` §7.12 for the full call map.

See `PROJECT_HANDOFF.md` for full architecture and deployment notes.
