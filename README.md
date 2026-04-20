# UP2U 🍜

> "Where do you want to eat?" "Up to you." — Never again.

UP2U is a real-time group dining decision app that turns the most annoying part of hanging out with friends into a party game. Everyone submits their food preferences, the AI reads the room, and the group gets a decisive restaurant recommendation — complete with personality roasts, group conflict analysis, and a dramatic reveal.

---

## The Problem

Every group chat has that one person who says "up to you" when asked where to eat. Then everyone says "up to you." Then nobody decides. Then you end up at the same place you always go.

UP2U solves group decision paralysis by making the process social, fast, and actually fun.

---

## How It Works

1. **Host creates a session** and shares a 6-character code or link with the group
2. **Everyone joins** on their phone — no app download, just a browser link
3. **Each person fills out a short survey** — hunger level, vibe, cuisine rankings, dietary restrictions
4. **The AI analyses the group** and generates a reveal with:
   - A personality roast for each person based on their food mood
   - What the group agrees on and where things get spicy
   - One decisive primary recommendation with a reason tied to your specific group
   - Two backup options
5. **Everyone sees the reveal simultaneously** on their own phones in real time

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React (mobile-first) |
| Backend | Python FastAPI |
| Real-time | WebSockets |
| Database | Redis |
| Restaurant Data | Google Places API |
| AI Reveal | Google Gemini 2.5 Flash |
| Deployment | Render (backend), Vercel (frontend) |

---

## Architecture

```
User's Phone (React)
      ↕ WebSocket / HTTP
FastAPI Backend (Python)
      ↕              ↕              ↕
    Redis      Google Places    Gemini AI
 (sessions)   (restaurants)  (reveal text)
```

The backend manages stateful sessions in Redis with TTL-based expiry. WebSockets push live events to all connected clients simultaneously — participant joins, survey submissions, and the final reveal all happen in real time without polling.

---

## Backend Features (Complete)

- `POST /create-session` — generates a unique session code, stores session state in Redis
- `POST /join-session/{code}` — adds participant, broadcasts join event to all connected clients
- `POST /start-session/{code}` — host starts the session, sets location
- `POST /submit-answers/{code}` — stores survey answers, triggers AI reveal when all participants submit
- `GET /session/{code}` — retrieves current session state
- `WebSocket /ws/{code}/{name}` — persistent connection for real-time event delivery

---

## AI Reveal Pipeline

When all participants submit:

1. Google Places API fetches nearby restaurants filtered by relevance, rating, and open status
2. Results are cleaned, deduplicated, and scored using haversine distance from the group's location
3. Top 6 restaurants by rating and review count are passed to Gemini along with all group preferences
4. Gemini returns structured JSON with personality lines, group analysis, and ranked recommendations
5. Result is broadcast to all connected WebSocket clients simultaneously

---

## Session Lifecycle

```
created (waiting) → active (survey in progress) → revealing (AI generating) → expired (TTL)
```

Sessions automatically expire after 1 hour. TTL is preserved across all Redis updates so joining or submitting doesn't reset the clock.

---

## Project Status

- [x] Backend — sessions, WebSockets, Places API, AI reveal pipeline
- [ ] Frontend — React mobile-first UI (in progress)
- [ ] Geocoding — convert address strings to coordinates
- [ ] Deployment — Render + Vercel

---

## Local Development

### Prerequisites
- Python 3.11+
- Docker (for Redis)
- Google Places API key
- Google Gemini API key

### Setup

```bash
# Clone the repo
git clone https://github.com/YOURUSERNAME/up2u.git
cd up2u/backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Fill in your API keys in .env

# Start Redis
docker run -d -p 6379:6379 redis

# Run the server
uvicorn main:app --reload
```

API explorer available at `http://localhost:8000/docs`

---

## Environment Variables

```
GOOGLE_PLACES_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
REDIS_URL=redis://localhost:6379
```

---

## Why This Project

Built to solve a real problem — the endless "up to you" loop that plagues every friend group. The technical challenge was interesting: coordinating real-time state across multiple simultaneous users, integrating live restaurant data with AI-generated personalised output, and making the whole thing feel like a social experience rather than a utility.
