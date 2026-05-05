"""
UP2U Backend — main.py
======================
FastAPI application for UP2U, a real-time group dining decision app.

Flow:
    1. Host creates a session → gets a 6-char code
    2. Participants join via that code
    3. Host starts the session
    4. Everyone fills out the survey and submits answers
    5. When all answers are in, the AI reveal is generated and broadcast

Session state lives in Redis with a 1-hour TTL.
Real-time events are pushed to clients over WebSockets.
"""

from fastapi import FastAPI, WebSocket
from google import genai
from dotenv import load_dotenv
import os
import redis
import random, string
import json
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import math

load_dotenv()

app = FastAPI()

# Allow all origins during development. Tighten this in production
# to only allow your frontend's domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

r = redis.Redis.from_url(os.getenv("REDIS_URL"))

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
# Pydantic models define and validate the shape of incoming request bodies.
# FastAPI uses these automatically — if the request doesn't match, it returns
# a 422 error before your code even runs.


class CreateSessionRequest(BaseModel):
    host_name: str


class JoinSessionRequest(BaseModel):
    participant_name: str


class StartSessionRequest(BaseModel):
    host_name: str
    location: str


class SubmitAnswersRequest(BaseModel):
    participant_name: str
    answers: dict


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by session code.

    Each session has a list of connected WebSockets. When an event happens
    (e.g. someone joins), we broadcast it to everyone in that session.

    Note: this is in-memory, so it won't work across multiple server
    instances. A production setup would use Redis pub/sub instead.
    """

    def __init__(self):
        # { "ABC123": [websocket1, websocket2, ...] }
        self.sessions: dict[str, list[WebSocket]] = {}

    async def connect(self, session_code: str, websocket: WebSocket):
        """Accept a new WebSocket and register it under the session code."""
        await websocket.accept()
        if session_code not in self.sessions:
            self.sessions[session_code] = []
        self.sessions[session_code].append(websocket)

    async def disconnect(self, session_code: str, websocket: WebSocket):
        """Remove a WebSocket when the client disconnects."""
        self.sessions[session_code].remove(websocket)

    async def broadcast(self, session_code: str, event: dict):
        """Send a JSON event to every connected client in the session."""
        if session_code not in self.sessions:
            return  # no one connected yet, nothing to do
        for ws in self.sessions[session_code]:
            await ws.send_text(json.dumps(event))


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Helper: Redis session key
# ---------------------------------------------------------------------------


def session_key(code: str) -> str:
    """Returns the Redis key for a given session code."""
    return f"session:{code}"


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def root():
    return {"message": "UP2U backend is alive"}


@app.post("/create-session")
def create_session(request: CreateSessionRequest):
    """
    Create a new session and return a 6-character join code.

    The code is uppercase alphanumeric (e.g. "X4K9PQ") so it's easy
    to share verbally. Session expires after 1 hour via Redis TTL.
    """
    new_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    session = {
        "code": new_code,
        "host": request.host_name,
        "status": "waiting",
        "location": None,
        "participants": [],
        "answers": {},
    }
    r.setex(session_key(new_code), 3600, json.dumps(session))
    return {"session_code": new_code}


@app.get("/session/{code}")
def get_session(code: str):
    """Return current session state. Used on page load/refresh."""
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}
    return json.loads(data)


@app.post("/join-session/{code}")
async def join_session(code: str, request: JoinSessionRequest):
    """
    Add a participant to the session and broadcast a participant_joined event.

    We preserve the existing TTL when writing back to Redis so that
    a participant joining doesn't accidentally extend the session lifetime.
    """
    key = session_key(code)
    ttl = r.ttl(key)  # preserve remaining TTL — don't reset to 3600
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    session = json.loads(data)
    session["participants"].append(request.participant_name)
    r.setex(key, ttl, json.dumps(session))

    await manager.broadcast(
        code,
        {
            "type": "participant_joined",
            "data": {
                "name": request.participant_name,
                "participants": session["participants"],
            },
        },
    )

    return {"session_code": code}


@app.post("/start-session/{code}")
async def start_session(code: str, request: StartSessionRequest):
    """
    Host starts the session, transitioning status from 'waiting' to 'active'.

    Broadcasts session_started so all lobby clients know to navigate
    to the survey. Only the host (matched by name) can call this.

    TODO: Replace name-based host check with a proper auth token.
    """
    key = session_key(code)
    ttl = r.ttl(key)
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    session = json.loads(data)

    if request.host_name != session["host"]:
        return {"error": "only the host can start the session"}

    session["status"] = "active"
    session["location"] = request.location
    r.setex(key, ttl, json.dumps(session))

    await manager.broadcast(
        code,
        {
            "type": "session_started",
            "data": {"location": request.location},
        },
    )

    return session


@app.post("/submit-answers/{code}")
async def submit_answers(code: str, request: SubmitAnswersRequest):
    """
    Record a participant's survey answers and broadcast answer_submitted.

    When every participant has submitted, this endpoint triggers the AI
    reveal automatically: it fetches nearby restaurants, calls Gemini,
    and broadcasts reveal_ready with the full reveal payload.

    The trigger logic is: len(answers) == len(participants).
    """
    key = session_key(code)
    ttl = r.ttl(key)
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    session = json.loads(data)

    if request.participant_name not in session["participants"]:
        return {"error": "participant not found in session"}

    session["answers"][request.participant_name] = request.answers
    r.setex(key, ttl, json.dumps(session))

    await manager.broadcast(
        code,
        {
            "type": "answer_submitted",
            "data": {
                "name": request.participant_name,
                "submitted": list(session["answers"].keys()),
                "total": len(session["participants"]),
            },
        },
    )

    # All answers in — generate and broadcast the reveal
    if len(session["answers"]) == len(session["participants"]):
        session["status"] = "revealing"

        # TODO: replace hardcoded coords with actual geocoding from session["location"]
        loc = [-37.8136, 144.9631]  # Melbourne CBD
        restaurants = get_nearby_restaurants(loc[0], loc[1])

        users = [{"name": name, **ans} for name, ans in session["answers"].items()]
        reveal = generate_reveal(users, restaurants)

        await manager.broadcast(code, {"type": "reveal_ready", "data": reveal})

    return session


@app.websocket("/ws/{session_code}/{participant_name}")
async def websocket_endpoint(
    websocket: WebSocket, session_code: str, participant_name: str
):
    """
    Persistent WebSocket connection for a participant in a session.

    The participant name is in the URL so the server knows who this
    socket belongs to without any auth handshake.

    Currently the server doesn't do anything with messages sent *from*
    clients — it just re-broadcasts them. All meaningful events are
    server-initiated (participant_joined, session_started, etc).
    """
    await manager.connect(session_code, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Re-broadcast any client message to the session
            await manager.broadcast(
                session_code,
                {
                    "type": "message",
                    "data": {"participant": participant_name, "message": data},
                },
            )
    except Exception:
        await manager.disconnect(session_code, websocket)


# ---------------------------------------------------------------------------
# Restaurant fetching (Google Places API)
# ---------------------------------------------------------------------------

# Place types that indicate a venue is NOT a restaurant we want to recommend
INVALID_TYPES = {
    "lodging",
    "hotel",
    "gym",
    "supermarket",
    "grocery_store",
    "gas_station",
    "pharmacy",
    "hospital",
    "school",
    "bank",
    "tourist_attraction",
    "historical_landmark",
    "shopping_mall",
}

# Generic types that appear on almost every place — not useful as cuisine tags
GENERIC_TYPES = {
    "restaurant",
    "food",
    "point_of_interest",
    "establishment",
    "store",
    "food_store",
}


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate straight-line distance between two lat/lng points in metres.

    Uses the Haversine formula, which accounts for Earth's curvature.
    Good enough for short distances like 'walking to a restaurant'.
    """
    R = 6371000  # Earth's radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def clean_restaurants(raw_places: list, user_lat: float, user_lng: float) -> list:
    """
    Filter and reshape raw Google Places API results into usable restaurant dicts.

    Filters out:
    - Non-restaurant venues (hotels, gyms, pharmacies, etc.)
    - Places without any food-related type tag

    Returns a list of dicts with consistent keys for the AI prompt.
    """
    cleaned = []
    for place in raw_places:
        types = place.get("types", [])

        if any(t in INVALID_TYPES for t in types):
            continue

        if not any(
            t in ["restaurant", "food", "cafe", "bar", "meal_takeaway"] for t in types
        ):
            continue

        cleaned.append(
            {
                "name": place.get("displayName", {}).get("text", "Unknown"),
                "rating": place.get("rating", 0),
                "review_count": place.get("userRatingCount", 0),
                "price_level": place.get("priceLevel", "Unknown"),
                "address": place.get("formattedAddress", ""),
                # Strip generic suffixes so cuisines read as e.g. "japanese" not "japanese_restaurant"
                "cuisines": [
                    t.replace("_restaurant", "").replace("_", " ")
                    for t in types
                    if t not in GENERIC_TYPES
                ],
                "summary": place.get("editorialSummary", {}).get("text", ""),
                "open_now": place.get("regularOpeningHours", {}).get("openNow", None),
                "maps_link": f"https://www.google.com/maps/place/?q=place_id:{place.get('id', '')}",
                "distance_meters": int(
                    haversine(
                        user_lat,
                        user_lng,
                        place["location"]["latitude"],
                        place["location"]["longitude"],
                    )
                ),
            }
        )
    return cleaned


def get_nearby_restaurants(latitude: float, longitude: float) -> list:
    """
    Fetch and clean restaurants within 500m of the given coordinates.

    Uses the Google Places API v1 (New) searchNearby endpoint.
    Returns up to 20 results, filtered through clean_restaurants.
    """
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        # FieldMask tells the API exactly which fields to return.
        # Only requesting what we need keeps the response small and avoids
        # being billed for fields we don't use.
        "X-Goog-FieldMask": (
            "places.displayName,places.rating,places.userRatingCount,"
            "places.priceLevel,places.formattedAddress,places.types,"
            "places.regularOpeningHours,places.editorialSummary,"
            "places.id,places.location"
        ),
    }
    body = {
        "includedTypes": ["restaurant"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": 500.0,
            }
        },
    }
    response = requests.post(url, headers=headers, json=body)
    raw = response.json().get("places", [])
    return clean_restaurants(raw, latitude, longitude)


# ---------------------------------------------------------------------------
# AI reveal generation (Google Gemini)
# ---------------------------------------------------------------------------


def generate_reveal(users: list[dict], restaurants: list[dict]) -> dict:
    """
    Generate the personality roasts and restaurant recommendation via Gemini.

    Steps:
    1. Pre-filter to only open restaurants, take top 6 by rating
    2. Format users and restaurants as plain text for the prompt
    3. Call Gemini with a system prompt defining the output format
    4. Parse and return the JSON response

    Args:
        users: List of participant dicts, each with name + survey answers
        restaurants: Cleaned restaurant dicts from get_nearby_restaurants

    Returns:
        Reveal dict matching the structure:
        {
            personality_lines: { name: line },
            agreements: str,
            conflicts: str,
            primary: { name, reason, maps_link },
            backups: [{ name, reason }]
        }
    """
    # Only consider places that are currently open, ranked by quality
    restaurants = [r for r in restaurants if r["open_now"] != False]
    restaurants = sorted(
        restaurants, key=lambda r: (r["rating"], r["review_count"]), reverse=True
    )[:6]

    # Format user preferences as a readable block for the prompt
    preferences_text = "\n".join(
        f"{u['name']}: hunger={u['hunger']}, vibe={u['vibe']}, "
        f"cuisines={u['cuisines_ranked']}, travel_distance={u['travel_distance']}, "
        f"dietary={u['dietary']}"
        for u in users
    )

    # Format restaurant data as a readable block for the prompt
    restaurants_text = "\n".join(
        f"{r['name']}: cuisines={r['cuisines']}, rating={r['rating']} "
        f"({r['review_count']} reviews), price_level={r['price_level']}, "
        f"distance_meters={r['distance_meters']}, open_now={r['open_now']}, "
        f"summary={r['summary']}, address={r['address']}, maps_link={r['maps_link']}"
        for r in restaurants
    )

    system_prompt = """You are a fun, hype-man AI helping a group of friends decide where to eat.
You're part of the group, not an outsider observing them.

Your job:
1. Write a SHORT roast-style personality line for each person based on their food mood
2. Summarise what the group agrees on and where they clash
3. Pick the single best restaurant and hype it up
4. Provide 2 backup options with punchy reasons

Rules for personality lines:
- MAX 10 words, roast-style but friendly
- Personality lines should roast the person's behaviour, not just describe their preferences
- Use deadpan humour, not just exclamation marks
- Talk TO the group directly, not about them

Personality line examples:
- "Someone REALLY needs their Thai fix right now 🌶️"
- "Apparently salads count as a meal, Sarah 🥗"
- "Would literally eat anything right now, no standards detected 🤤"
- "Came for the vibes, the food is secondary apparently 😌"  
- "One person vetoed everything fun with their dietary restrictions 🥬"
- "Ranked every cuisine the same. Thanks for the input, Josh."

Rules for agreements and conflicts:
- Speak as part of the group — use "everyone", "most of us", "almost everyone"
- NEVER say "they both" or "they" — you are IN the group
- Make it fun — add relevant emoji, a joke, a little drama
- MAX 15 words each
- Example agreements: "Everyone's starving and nobody wants to travel far 🏃"
- Example conflicts: "Half of us want quick bites, the other half want a vibe 👀"

Rules for primary reason:
- 2 sentences max, hype it up like you're genuinely excited
- Explain why it works for THIS specific group

Rules for backup reasons:
- 1 sentence, punchy

Other rules:
- Respect dietary restrictions strictly, never recommend somewhere a person can't eat
- Prefer open, highly rated, highly reviewed places
- Return ONLY valid JSON, no explanation, no markdown backticks"""

    user_prompt = f"""Group preferences:
{preferences_text}

Restaurants:
{restaurants_text}

Return this exact JSON structure:
{{
  "personality_lines": {{"name": "line"}},
  "agreements": "...",
  "conflicts": "...",
  "primary": {{"name": "...", "reason": "...", "maps_link": "..."}},
  "backups": [{{"name": "...", "reason": "..."}}]
}}"""

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config={"system_instruction": system_prompt},
        contents=user_prompt,
    )

    raw = response.text.strip()
    print(f"Gemini raw response: '{raw}'")

    # Strip markdown code fences if the model wrapped the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


# ---------------------------------------------------------------------------
# Dev/test endpoints — remove before deploying to production
# ---------------------------------------------------------------------------


@app.get("/test-places")
def test_places():
    """Smoke test for the Places API integration."""
    return get_nearby_restaurants(-37.8136, 144.9631)


@app.get("/test-reveal")
def test_reveal():
    """Smoke test for the full reveal pipeline with hardcoded users."""
    restaurants = get_nearby_restaurants(-37.8136, 144.9631)
    users = [
        {
            "name": "Chris",
            "hunger": 5,
            "vibe": "quick",
            "cuisines_ranked": ["japanese", "thai"],
            "travel_distance": "walking",
            "dietary": [],
        },
        {
            "name": "Sarah",
            "hunger": 2,
            "vibe": "chill",
            "cuisines_ranked": ["italian", "greek"],
            "travel_distance": "don't care",
            "dietary": ["vegetarian"],
        },
    ]
    return generate_reveal(users, restaurants)
