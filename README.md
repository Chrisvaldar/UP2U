# UP2U

UP2U is a real-time group dining decision app: create a session, collect group preferences, and reveal a restaurant pick with AI-generated personality lines.

**Live app:** [https://up2u-app.vercel.app/](https://up2u-app.vercel.app/)

## Architecture

- `frontend/`: React 19, Vite 8, TypeScript, Tailwind 4, React Router, Axios, Google Maps Places autocomplete, dnd-kit ranking UI, Embla reveal carousel (outer restaurant slides + inner photo carousel per card). Hosted on **Vercel** (`frontend/` root).
- `backend/`: FastAPI, Redis session storage, WebSockets, Google Places, Gemini reveal generation, optional Groq fallback. Hosted on **Railway** (`backend/` root) with Railway **Redis**.
- Redis stores session state with a one-hour TTL. Successful reveals also store the full `reveal` payload in Redis (`status: "revealed"`).
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
| Server | `backend/.env` → `GOOGLE_PLACES_API_KEY` | API restrictions applied (Places API New + Photo Media); no website restriction — **restart uvicorn** after changing |

If `/test-places` returns 404, set `DEBUG=true`. A bad server key returns **502** (not silent `[]`). Legitimate empty search returns `[]` with **200**.

## CI

GitHub Actions workflow: `.github/workflows/UP2U.yaml`

On push/PR to `main`, two jobs run in parallel:

- **backend** — `pip install -r backend/requirements.txt`, then `cd backend && pytest` (fakeredis; no secrets)
- **frontend** — `cd frontend && npm install && npm run build`

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
copy .env.example .env
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

**Session errors:** `HTTPException` with `{"detail": "<message>"}` — **404** (not found), **403** (host-only), **409** (state conflict). Frontend reads `err.response.data.detail` in axios `catch` blocks.

**Upstream errors:** Google Places, Geocoding, and AI failures map to **502** (bad upstream response), **503** (unavailable / rate-limited), **504** (timeout) via `upstream_to_http()`. Generic client messages; full detail is server-logged only.

- `GET /`: health check.
- `POST /create-session`: creates a session and returns `{ "code": "ABC123" }`.
- `GET /session/{code}`: returns session JSON; **404** if missing. Includes `reveal` when `status` is `"revealed"`.
- `POST /join-session/{code}`: adds a participant and broadcasts `participant_joined`; **404** if missing, **409** if session is `revealing`, `revealed`, or `reveal_failed`.
- `POST /start-session/{code}`: host-only; fetches nearby cuisines via Places; broadcasts `session_started`; **403** if not host; **502/503/504** if Places fails (empty `cuisines` on successful zero-result search is still **200**).
- `POST /submit-answers/{code}`: stores answers, broadcasts `answer_submitted`, runs reveal pipeline when everyone has submitted; **404** if session or participant not found. Pipeline success → **HTTP 200** + `status: revealed` + `reveal` in session JSON + WebSocket `reveal_ready`. Pipeline failure → **HTTP 200** + `status: reveal_failed` + WebSocket `reveal_failed` (not 502).
- `POST /retry-session/{code}`: host-only retry after `reveal_failed`; clears answers, broadcasts `retrying`; **403** / **409** as applicable.
- `POST /end-session/{code}`: host-only; broadcasts `session_ended`, deletes Redis session; **403** if not host.
- `GET /photo/{place_id}/{index}`: server-side photo proxy; **404** if no photo at index; **502/503/504** on upstream fetch failure.
- `GET /test-places`, `GET /test-reveal`, `GET /test-geocode`: dev smoke tests (`DEBUG=true`; **404** when disabled; propagate **502/503/504** on upstream failure).
- `WS /ws/{session_code}/{participant_name}`: live session event stream.

## WebSocket Events

- `participant_joined`: `{ name, participants }`
- `session_started`: `{ host, lat, lng, participants, cuisines }`
- `answer_submitted`: `{ name, submitted, total }`
- `reveal_ready`: full reveal payload with personality lines, agreements, conflicts, primary restaurant, backups, and optional `photo_urls` per restaurant (served via `/photo/...` proxy).
- `reveal_failed`: `{ error }`
- `retrying`: `{ message }`
- `session_ended`: `{ message }`

## Frontend Pages

- `/`: create or join a session with validation, loading state, and error handling.
- `/lobby/:code`: shows participants, lets the host choose a Google Places location, and starts the session.
- `/survey/:code`: collects hunger, vibe, ranked cuisines, travel distance, and dietary requirements. Steps 0–4 persist to sessionStorage (`saveDraft`/`getDraft`); restore on refresh until submit. Reload with `status: revealed` hydrates reveal from API and navigates to Reveal.
- `/reveal/:code`: personality slides, agreements/conflicts, restaurant carousel with photo carousels per card; reveal read from `sessionStorage` (`getReveal`).

## Verification

```powershell
cd frontend
npm.cmd run build

cd ..\backend
venv\Scripts\python.exe -m pytest
```

Backend tests (`backend/tests/test_sessions.py`, 29 tests) use **fakeredis** via autouse fixture in `backend/tests/conftest.py` — no real Redis required. Coverage includes session CRUD, join conflicts, TTL preservation, `start-session` upstream errors, reveal pipeline success (`revealed` + Redis `reveal`) / failure / retry, DEBUG-gated dev routes, photo proxy errors, and WebSocket broadcast. Config: `backend/pytest.ini` (`pythonpath = .`, `testpaths = tests`).

CI runs the same checks on every push/PR to `main` (see **CI** above).

## Known Limitations

- WebSocket connections are in-memory and are not multi-instance safe (single Railway instance is fine for friends beta).
- Reveal page requires `getReveal(code)` in sessionStorage — direct `/reveal/:code` without prior save redirects home (Survey reload with `status: revealed` recovers from API).
- Reveal carousel slide index resets on refresh.

Backend logs session lifecycle, reveal success/failure (typed `UpstreamError` vs unexpected exceptions), Places/photo/geocode errors, and AI JSON parse failures via Python `logging`. See `PROJECT_HANDOFF.md` §7.12 for the full call map.

See `PROJECT_HANDOFF.md` for full architecture and deployment notes.
