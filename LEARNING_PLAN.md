# UP2U — 1-Week Full-Stack Learning Sprint

> Rebuild UP2U yourself. The existing `backend/` and `frontend/` folders are your **answer key** — read them for specs, never copy-paste.

**Folder:** All new code goes in `UP2U-learn/`. Start with `UP2U-learn/backend/`.

---

## Rules

1. **Read** the reference code → **close it** → build from scratch in `UP2U-learn/`.
2. **No copy-paste** from the AI-built version.
3. After each day, add an entry to `UP2U-learn/backend/LEARNING.md` (5 sentences: what you built, what confused you, what's next).
4. Test manually before moving on (`/docs`, curl, two browser tabs).
5. AI is OK for *explanations* and *debugging after you tried* — not for writing whole files.

---

## React vs Next.js (decision)

**Use React + Vite** (same as reference frontend). UP2U is a real-time SPA — WebSockets, session flows, no SEO need. Next.js adds SSR complexity you don't need this week.

---

## Reference architecture

```
Phone (React)  ↔  HTTP + WebSocket  ↔  FastAPI
                                          ↕
                    Redis    Google Places    Gemini
```

**Session lifecycle:** `waiting` → `active` → `revealing` → expired (1h TTL)

**Endpoints to implement:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check |
| POST | `/create-session` | Create session, return 6-char code |
| GET | `/session/{code}` | Get session state |
| POST | `/join-session/{code}` | Add participant |
| POST | `/start-session/{code}` | Host starts, set location |
| POST | `/submit-answers/{code}` | Store answers; trigger reveal when all in |
| WS | `/ws/{code}/{name}` | Real-time events |

**WebSocket events (server → client):** `participant_joined`, `session_started`, `answer_submitted`, `reveal_ready`

---

## Day 1 — Backend foundation (Mon)

**Goal:** FastAPI app + Redis + create/get session.

| # | Task | Done |
|---|------|------|
| 1 | Create venv, `pip install -r requirements.txt` | ☐ |
| 2 | Start Redis: `docker run -d -p 6379:6379 redis` | ☐ |
| 3 | Copy `.env.example` → `.env`, set `REDIS_URL=redis://localhost:6379` | ☐ |
| 4 | Implement `GET /` health check | ☐ |
| 5 | Implement `POST /create-session` — 6-char code, store JSON in Redis with `SETEX` (3600s) | ☐ |
| 6 | Implement `GET /session/{code}` — return session or error | ☐ |
| 7 | Add Pydantic models: `CreateSessionRequest` | ☐ |
| 8 | Test in Swagger: `http://localhost:8000/docs` | ☐ |

**Session JSON shape:**
```json
{
  "code": "X4K9PQ",
  "host": "Chris",
  "status": "waiting",
  "location": null,
  "participants": [],
  "answers": {}
}
```

**Run:** `uvicorn main:app --reload`

**Checkpoint:** Create a session, GET it back, confirm TTL with `redis-cli TTL session:YOURCODE`.

---

## Day 2 — Session flow (Tue)

**Goal:** Join, start, submit — full HTTP flow without WebSockets.

| # | Task | Done |
|---|------|------|
| 1 | `POST /join-session/{code}` — append participant, **preserve TTL** (`TTL` then `SETEX`) | ☐ |
| 2 | `POST /start-session/{code}` — host only, set `status: active`, set `location` | ☐ |
| 3 | `POST /submit-answers/{code}` — store answers dict keyed by participant name | ☐ |
| 4 | When `len(answers) == len(participants)`, set `status: revealing` (reveal logic tomorrow) | ☐ |
| 5 | Return proper errors: session not found, not host, participant not in session | ☐ |
| 6 | Write 3+ pytest tests (create, join, start) | ☐ |

**Checkpoint:** Full HTTP flow via `/docs` — create → join (2 users) → start → both submit.

---

## Day 3 — WebSockets (Wed)

**Goal:** Real-time broadcasts.

| # | Task | Done |
|---|------|------|
| 1 | Build `ConnectionManager` — dict of session_code → list of WebSockets | ☐ |
| 2 | `WebSocket /ws/{code}/{name}` — accept, register, disconnect on close | ☐ |
| 3 | Broadcast `participant_joined` on join | ☐ |
| 4 | Broadcast `session_started` on start | ☐ |
| 5 | Broadcast `answer_submitted` on submit (include submitted count + total) | ☐ |
| 6 | Test with two browser tabs using a WebSocket client or wscat | ☐ |

**Checkpoint:** Join in tab A, see update in tab B instantly.

---

## Day 4 — External APIs + AI reveal (Thu)

**Goal:** Places API, Gemini, full backend done.

| # | Task | Done |
|---|------|------|
| 1 | Add API keys to `.env` (`GOOGLE_PLACES_API_KEY`, `GEMINI_API_KEY`) | ☐ |
| 2 | `get_nearby_restaurants(lat, lng)` — Places API searchNearby, 500m radius | ☐ |
| 3 | `clean_restaurants()` — filter invalid types, add haversine distance | ☐ |
| 4 | `generate_reveal(users, restaurants)` — Gemini prompt → JSON | ☐ |
| 5 | Wire reveal into submit when all answers in; broadcast `reveal_ready` | ☐ |
| 6 | Geocode `session["location"]` OR hardcode coords for now (note in LEARNING.md) | ☐ |
| 7 | Split into `models.py`, `services/places.py`, `services/reveal.py` if time | ☐ |

**Checkpoint:** Full backend flow with real APIs — two participants submit → reveal JSON returned.

---

## Day 5 — Frontend core (Fri)

**Goal:** Vite + React app, static pages + API calls.

```bash
cd UP2U-learn
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install axios react-router-dom
npm run dev
```

| # | Task | Done |
|---|------|------|
| 1 | Routes: `/`, `/lobby/:code`, `/survey/:code`, `/reveal/:code` | ☐ |
| 2 | HomePage — create session + join session forms (axios → backend) | ☐ |
| 3 | LobbyPage — fetch session, show participants list | ☐ |
| 4 | Host "Start" button → `POST /start-session` | ☐ |
| 5 | SurveyPage — hunger, vibe, cuisines, dietary form → submit | ☐ |
| 6 | RevealPage — display personality lines, primary, backups | ☐ |

**Checkpoint:** Full flow works with manual refresh (no WebSocket yet).

---

## Day 6 — Frontend real-time + polish (Sat)

**Goal:** WebSocket wiring + mobile UI.

| # | Task | Done |
|---|------|------|
| 1 | LobbyPage WebSocket — live participant list | ☐ |
| 2 | Auto-navigate to survey on `session_started` | ☐ |
| 3 | Survey waiting state on `answer_submitted` | ☐ |
| 4 | Auto-navigate to reveal on `reveal_ready` | ☐ |
| 5 | Mobile-first Tailwind layout | ☐ |
| 6 | `VITE_API_URL` env var for API base | ☐ |
| 7 | End-to-end test: 3 browser windows, one host | ☐ |

**Checkpoint:** Friends can join from phones on same WiFi (`uvicorn --host 0.0.0.0`).

---

## Day 7 — Tests, DevOps, deploy (Sun)

**Goal:** CI, Docker, live URL.

| # | Task | Done |
|---|------|------|
| 1 | pytest suite: unit (haversine, clean_restaurants) + API tests | ☐ |
| 2 | `docker-compose.yml` — Redis + backend | ☐ |
| 3 | `Dockerfile` for backend | ☐ |
| 4 | GitHub Actions — run pytest on push | ☐ |
| 5 | Deploy backend → Render or Railway + Upstash Redis | ☐ |
| 6 | Deploy frontend → Vercel with `VITE_API_URL` | ☐ |
| 7 | Write `docs/ARCHITECTURE.md` — diagram, scaling limits, Redis schema | ☐ |
| 8 | Tighten CORS to your frontend domain only | ☐ |

**Checkpoint:** Public URL. Share link. Complete a session with friends.

---

## DevOps cheat sheet

**Local:**
```bash
docker run -d -p 6379:6379 redis
cd UP2U-learn/backend && uvicorn main:app --reload
cd UP2U-learn/frontend && npm run dev
```

**Deploy (simple path):**
- Backend: Render Web Service + Upstash Redis (free tier)
- Frontend: Vercel (connect repo, set env vars)
- Secrets: only on backend, never in frontend repo

**AWS (after this week):** ECS Fargate + ElastiCache + CloudFront — same concepts, more control.

---

## When stuck

1. Read the matching section in reference `backend/main.py` — understand, don't copy.
2. Check FastAPI docs: https://fastapi.tiangolo.com
3. Ask AI: "Explain why Redis TTL needs to be preserved on update" (not "write my endpoint").
4. Compare your `/docs` request/response to reference behavior.

---

## After the week

- Host auth tokens (replace name-based host check)
- Redis pub/sub for multi-server WebSockets
- Playwright E2E tests
- Rate limiting, Sentry, structured logging
- Learn Next.js by rebuilding the landing page
- AWS deep dive (ECS, ElastiCache, ALB)
