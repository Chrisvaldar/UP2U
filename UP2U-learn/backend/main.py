"""
UP2U Learn — Backend
====================
Rebuild the UP2U backend yourself. Reference: ../../backend/main.py

Day 1 goals:
  - GET  /                  health check
  - POST /create-session    6-char code, store in Redis (1h TTL)
  - GET  /session/{code}    return session JSON or error

Run:
  uvicorn main:app --reload

Docs:
  http://localhost:8000/docs
"""

import os
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from dotenv import load_dotenv
import redis
import random
import string
import json
import math
import requests

load_dotenv()
r = redis.Redis.from_url(os.getenv("REDIS_URL"))
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

app = FastAPI(title="UP2U Learn")


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


def session_key(code: str) -> str:
    return f"session:{code}"


@app.get("/")
def health():
    return {"message": "It's alive!"}


@app.post("/create-session")
def create_session(request: CreateSessionRequest):
    ttl_seconds = 3600

    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    session = {
        "code": code,
        "host": request.host_name,
        "status": "waiting",
        "location": None,
        "participants": [],
        "answers": {},
    }

    r.setex(session_key(code), ttl_seconds, json.dumps(session))

    return {"code": code}


@app.get("/session/{code}")
def get_session(code: str):
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}
    return json.loads(data)


@app.post("/join-session/{code}")
async def join_session(request: JoinSessionRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}

    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))

    session["participants"].append(request.participant_name)
    r.setex(session_key(code), ttl_seconds, json.dumps(session))

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

    return session


@app.post("/start-session/{code}")
async def start_session(request: StartSessionRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}
    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))

    if request.host_name == session["host"]:
        session["status"] = "active"
        session["location"] = request.location

        r.setex(session_key(code), ttl_seconds, json.dumps(session))
        await manager.broadcast(
            code,
            {
                "type": "session_started",
                "data": {
                    "host": request.host_name,
                    "location": request.location,
                    "participants": session["participants"],
                },
            },
        )
        return session

    return {"error": "Only the host can start the session"}


@app.post("/submit-answers/{code}")
async def submit_answers(request: SubmitAnswersRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        return {"error": "session not found"}

    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))

    if request.participant_name not in session["participants"]:
        return {"error": "Participant not found"}
    session["answers"][request.participant_name] = request.answers

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

    if len(session["answers"]) == len(session["participants"]):
        session["status"] = "revealing"
        users = [{"name": name, **ans} for name, ans in session["answers"].items()]
        radius = get_search_radius(users)

        loc = [-37.8136, 144.9631]  # Melbourne until geocoding
        restaurants = get_nearby_restaurants(loc[0], loc[1], radius)
        reveal = generate_reveal(users, restaurants)  
        await manager.broadcast(code, {"type": "reveal_ready", "data": reveal})

    r.setex(session_key(code), ttl_seconds, json.dumps(session))
    return session


@app.websocket("/ws/{session_code}/{participant_name}")
async def websocket_endpoint(
    websocket: WebSocket, session_code: str, participant_name: str
):
    await manager.connect(session_code, websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        await manager.disconnect(session_code, websocket)


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

TRAVEL_LIMITS = {
    "short walk (<500m)": 500,
    "public transport (<2km)": 2000,
    "don't mind": 3000,
}
DEFAULT_TRAVEL_LIMIT = 500  # conservative fallback if answer missing


def get_search_radius(users: list[dict]) -> float:
    """How far the group is willing to travel — limited by the strictest person."""
    limits = [
        TRAVEL_LIMITS.get(u.get("travel_distance", ""), DEFAULT_TRAVEL_LIMIT)
        for u in users
    ]
    return min(limits) if limits else DEFAULT_TRAVEL_LIMIT

def get_nearby_restaurants(latitude: float, longitude: float, radius: float = 500) -> list:
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
                "radius": radius,
            }
        },
    }
    response = requests.post(url, headers=headers, json=body)
    raw = response.json().get("places", [])
    restaurants = clean_restaurants(raw, latitude, longitude)
    return [r for r in restaurants if r["distance_meters"] <= radius]

@app.get("/test-places")
def test_places(radius: float = 500):
    return get_nearby_restaurants(-37.8136, 144.9631, radius)
# TODO (Day 4): Places API + Gemini reveal pipeline
