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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

r = redis.Redis.from_url(os.getenv("REDIS_URL"))

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


class CreateSessionRequest(BaseModel):
    host_name: str


class JoinSessionRequest(BaseModel):
    participant_name: str


class StartSessionRequest(BaseModel):
    host_name: str
    location: str


class SubmitAnswersRequest(BaseModel):
    participant_name: str
    answer: str


class ConnectionManager:
    def __init__(self):
        # stores connections grouped by session code
        # {"ABC123": [websocket1, websocket2, websocket3]}
        self.sessions = {}

    async def connect(self, session_code: str, websocket: WebSocket):
        # add this websocket to the session's list
        await websocket.accept()
        if session_code not in self.sessions:
            self.sessions[session_code] = []
        self.sessions[session_code].append(websocket)

    async def disconnect(self, session_code: str, websocket: WebSocket):
        # remove this websocket from the session's list
        self.sessions[session_code].remove(websocket)

    async def broadcast(self, session_code: str, event: dict):
        # send message to every websocket in the session
        for ws in self.sessions[session_code]:
            await ws.send_text(json.dumps(event))


manager = ConnectionManager()


@app.get("/")
def root():
    return {"message": "UP2U backend is alive"}


@app.post("/create-session")
def create_session(request: CreateSessionRequest):
    new_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    key = f"session:{new_code}"
    session = {
        "code": new_code,
        "host": request.host_name,
        "status": "waiting",
        "location": None,
        "participants": [],
        "answers": {},
    }
    r.setex(key, 3600, json.dumps(session))

    return {"session_code": new_code}


@app.get("/session/{code}")
def get_session(code: str):
    key = f"session:{code}"
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    return json.loads(data)


@app.post("/join-session/{code}")
async def join_session(code: str, request: JoinSessionRequest):
    key = f"session:{code}"
    ttl = r.ttl(key)
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    dict_data = json.loads(data)
    dict_data["participants"].append(request.participant_name)

    r.setex(key, ttl, json.dumps(dict_data))

    await manager.broadcast(
        code,
        {
            "type": "participant_joined",
            "data": {
                "name": request.participant_name,
                "participants": dict_data["participants"],
            },
        },
    )

    return {"session_code": code}


@app.post("/start-session/{code}")
async def start_session(code: str, request: StartSessionRequest):
    key = f"session:{code}"
    ttl = r.ttl(key)
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    dict_data = json.loads(data)

    if request.host_name != dict_data["host"]:
        return "Only the host can start the session"

    dict_data["status"] = "active"
    dict_data["location"] = request.location

    r.setex(key, ttl, json.dumps(dict_data))

    await manager.broadcast(
        code, {"type": "session_started", "data": {"location": request.location}}
    )

    return dict_data


@app.post("/submit-answers/{code}")
async def submit_answers(code: str, request: SubmitAnswersRequest):
    key = f"session:{code}"
    ttl = r.ttl(key)
    data = r.get(key)

    if data is None:
        return {"error": "session not found"}

    dict_data = json.loads(data)

    if request.participant_name not in dict_data["participants"]:
        return "Participant name not found in session"

    dict_data["answers"][request.participant_name] = request.answer

    if len(dict_data["answers"]) == len(dict_data["participants"]):
        # everyone has submitted
        dict_data["status"] = "revealing"
        # trigger AI + Places API call

    r.setex(key, ttl, json.dumps(dict_data))

    await manager.broadcast(
        code,
        {
            "type": "answer_submitted",
            "data": {
                "name": request.participant_name,
                "submitted": list(dict_data["answers"].keys()),
                "total": len(dict_data["participants"]),
            },
        },
    )

    # and if everyone submitted:
    if len(dict_data["answers"]) == len(dict_data["participants"]):
        await manager.broadcast(code, {"type": "all_submitted", "data": {}})

    return dict_data


@app.websocket("/ws/{session_code}/{participant_name}")
async def websocket_endpoint(
    websocket: WebSocket, session_code: str, participant_name: str
):
    await manager.connect(session_code, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # for now just broadcast whatever message we receive to everyone
            await manager.broadcast(session_code, f"{participant_name}: {data}")
    except Exception:
        await manager.disconnect(session_code, websocket)


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

GENERIC_TYPES = {
    "restaurant",
    "food",
    "point_of_interest",
    "establishment",
    "store",
    "food_store",
}


def haversine(lat1, lng1, lat2, lng2):
    R = 6371000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def clean_restaurants(raw_places: list, user_lat: float, user_lng: float):
    cleaned = []
    for place in raw_places:
        types = place.get("types", [])

        # skip if it's clearly not a restaurant
        if any(t in INVALID_TYPES for t in types):
            continue

        # must have at least "restaurant" or "food" somewhere
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


def get_nearby_restaurants(latitude: float, longitude: float):
    url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.priceLevel,places.formattedAddress,places.types,places.regularOpeningHours,places.editorialSummary,places.id,places.location",
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


@app.get("/test-places")
def test_places():
    return get_nearby_restaurants(-37.8136, 144.9631)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def generate_reveal(users: list[dict], restaurants: list[dict]) -> dict:
    # prefilter first
    restaurants = [r for r in restaurants if r["open_now"] != False]
    restaurants = sorted(
        restaurants, key=lambda r: (r["rating"], r["review_count"]), reverse=True
    )[:6]

    preferences_text = []
    for user in users:
        preferences_text.append(
            f"{user['name']}: hunger={user['hunger']}, vibe={user['vibe']}, cuisines={user['cuisines_ranked']}, travel_distance={user['travel_distance']}, dietary={user['dietary']}"
        )
    preferences_text = "\n".join(preferences_text)

    restaurants_text = []
    for r in restaurants:
        restaurants_text.append(
            f"{r['name']}: cuisines={r['cuisines']}, rating={r['rating']} ({r['review_count']} reviews), price_level={r['price_level']}, distance_meters={r['distance_meters']}, open_now={r['open_now']}, summary={r['summary']}, address={r['address']}, maps_link={r['maps_link']}"
        )
    restaurants_text = "\n".join(restaurants_text)

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
    print(f"AI response: '{raw}'")
    # strip markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)


@app.get("/test-reveal")
def test_reveal():
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
