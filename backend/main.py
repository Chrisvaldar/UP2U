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
from urllib.parse import quote
from google import genai
from google.genai.errors import ClientError, ServerError
from groq import Groq
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import asyncio
from collections import defaultdict
from fastapi import HTTPException
import logging
from pathlib import Path

load_dotenv()
r = redis.Redis.from_url(os.getenv("REDIS_URL"))
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

LOG_DIR = Path(__file__).resolve().parent / "logs"

handlers=[
        
        logging.StreamHandler(),
    ]
if DEBUG:
    LOG_DIR.mkdir(exist_ok=True)
    handlers.append(logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"))    

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="UP2U Learn")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://up2u-app.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    lat: float
    lng: float


class SubmitAnswersRequest(BaseModel):
    participant_name: str
    answers: dict


class RetrySessionRequest(BaseModel):
    host_name: str


class EndSessionRequest(BaseModel):
    host_name: str


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
        "participants": [request.host_name],
        "answers": {},
    }

    r.setex(session_key(code), ttl_seconds, json.dumps(session))
    logger.info(f"Session {code} created by {request.host_name}")
    return {"code": code}


@app.get("/session/{code}")
def get_session(code: str):
    data = r.get(session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return json.loads(data)


@app.post("/join-session/{code}")
async def join_session(request: JoinSessionRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = json.loads(data)
    # Preserve the original expiry so normal activity does not extend a session.
    ttl_seconds = r.ttl(session_key(code))

    if session["status"] == "revealing" or session["status"] == "reveal_failed":
        logger.warning(f"Join rejected for {code}: session status is {session['status']}")
        raise HTTPException(status_code=409, detail="Uh oh! The group has decided already :(")
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
    logger.info(f"{request.participant_name} joined session {code}")
    return session


@app.post("/start-session/{code}")
async def start_session(request: StartSessionRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))

    if request.host_name == session["host"]:
        session["status"] = "active"
        session["lat"] = request.lat
        session["lng"] = request.lng
        cuisines = location_to_cuisines(session["lat"], session["lng"])
        session["cuisines"] = cuisines

        # Preserve the original expiry so normal activity does not extend a session.
        r.setex(session_key(code), ttl_seconds, json.dumps(session))
        await manager.broadcast(
            code,
            {
                "type": "session_started",
                "data": {
                    "host": request.host_name,
                    "lat": request.lat,
                    "lng": request.lng,
                    "participants": session["participants"],
                    "cuisines": cuisines,
                },
            },
        )
        logger.info(f"Session {code} started by {request.host_name} at ({request.lat}, {request.lng}) → cuisines: {cuisines}")
        return session

    raise HTTPException(status_code=403, detail="Only the host can start the session.")


@app.post("/submit-answers/{code}")
async def submit_answers(request: SubmitAnswersRequest, code: str):
    data = r.get(session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = json.loads(data)
    # Preserve the original expiry so normal activity does not extend a session.
    ttl_seconds = r.ttl(session_key(code))

    if request.participant_name not in session["participants"]:
        raise HTTPException(status_code=404, detail="Participant not found")
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
        r.setex(session_key(code), ttl_seconds, json.dumps(session))
        lat = session["lat"]
        lng = session["lng"]
        users = [{"name": name, **ans} for name, ans in session["answers"].items()]
        try:
            # The reveal pipeline performs blocking HTTP/AI calls; keep the event loop responsive.
            reveal = await asyncio.to_thread(run_reveal_pipeline, users, lat, lng)
            await manager.broadcast(code, {"type": "reveal_ready", "data": reveal})
            logger.info(f"Reveal succeeded for {code} → primary: {reveal['primary']['name']}, backups: {[b['name'] for b in reveal['backups']]}")
        except Exception:
            session["status"] = "reveal_failed"
            r.setex(session_key(code), ttl_seconds, json.dumps(session))
            logger.exception(f"Reveal pipeline failed for session {code}")
            await manager.broadcast(
                code,
                {"type": "reveal_failed", "data": {"error": "Oops! Reveal failed"}},
            )
    r.setex(session_key(code), ttl_seconds, json.dumps(session))
    return session


@app.post("/retry-session/{code}")
async def retry_session(code: str, request: RetrySessionRequest):
    data = r.get(session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = json.loads(data)
    ttl_seconds = r.ttl(session_key(code))
    if request.host_name == session["host"]:
        if session["status"] != "reveal_failed":
            raise HTTPException(status_code=409, detail="Retry is only available if pipeline fails")

        session["status"] = "active"
        session["answers"] = {}
        r.setex(session_key(code), ttl_seconds, json.dumps(session))
        await manager.broadcast(
            code, {"type": "retrying", "data": {"message": "attempting retry"}}
        )
        return session
    raise HTTPException(status_code=403, detail="Only the host can retry the session.")


@app.post("/end-session/{code}")
async def end_session(code: str, request: EndSessionRequest):
    data = r.get(session_key(code))
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = json.loads(data)
    if request.host_name == session["host"]:
        await manager.broadcast(
            code, {"type": "session_ended", "data": {"message": "end of session"}}
        )

        r.delete(session_key(code))
        return session
    raise HTTPException(status_code=403, detail="Only the host can end the session.")


@app.websocket("/ws/{session_code}/{participant_name}")
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
    "corporate_office",
}

# primaryType values that end in _restaurant but aren't cuisines for the survey
NON_CUISINE_PRIMARY_TYPES = {
    "chicken_restaurant",
    "dessert_restaurant",
    "fast_food_restaurant",
    "breakfast_restaurant",
    "vegetarian_restaurant",
    "vegan_restaurant",
}

# Trailing segments stripped to get the base cuisine (e.g. korean_barbecue -> korean)
VENUE_MODIFIERS = {
    "barbecue",
    "bbq",
    "grill",
    "buffet",
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

    Returns a list of dicts with consistent keys for the AI prompt,
    including primary_type (Google's single main label per place).
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
                "primary_type": place.get("primaryType"),
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


def cuisine_from_primary_type(primary_type: str | None) -> str | None:
    """
    Derive a survey cuisine label from a Google Places primaryType.

    Only types ending in _restaurant are considered — venue categories
    like cafe and bar are excluded automatically. Non-cuisine restaurant
    types (dessert, fast food) are skipped via NON_CUISINE_PRIMARY_TYPES.
    Compound types such as korean_barbecue_restaurant normalize to the
    base cuisine (korean).
    """
    if not primary_type or not primary_type.endswith("_restaurant"):
        return None
    if primary_type in NON_CUISINE_PRIMARY_TYPES:
        return None

    stem = primary_type[: -len("_restaurant")]
    parts = stem.split("_")
    if len(parts) > 1 and parts[-1] in VENUE_MODIFIERS:
        stem = "_".join(parts[:-1])

    return stem.replace("_", " ") if stem else None


def location_to_cuisines(lat: float, lng: float) -> list[str]:
    """
    Return up to 5 nearby cuisine labels for the survey.

    Counts one vote per restaurant using primary_type only, so generic
    tags (cafe, bakery, etc.) cannot dominate the frequency ranking.
    """
    restaurants = get_nearby_restaurants(lat, lng, 2000)
    cuisines = defaultdict(int)
    for restaurant in restaurants:
        cuisine = cuisine_from_primary_type(restaurant.get("primary_type"))
        if cuisine:
            cuisines[cuisine] += 1
    ranked = sorted(cuisines, key=cuisines.get, reverse=True)
    return ranked[:5]


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


def get_nearby_restaurants(
    latitude: float, longitude: float, radius: float = 500
) -> list:
    """
    Fetch and clean restaurants within a certain radius of the given coordinates.

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
            "places.primaryType,places.regularOpeningHours,"
            "places.editorialSummary,places.id,places.location"
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
    if response.status_code != 200:
        logger.error(
            f"Getting restaurants failed with code {response.status_code} and body: {response.text}"
        )
    raw = response.json().get("places", [])
    restaurants = clean_restaurants(raw, latitude, longitude)
    return restaurants


@app.get("/test-places")
def test_places(radius: float = 500):
    if not DEBUG:
        raise HTTPException(status_code=404, detail="Dev endpoint: Not found")
    return get_nearby_restaurants(-37.8136, 144.9631, radius)


def rank_restaurants_for_group(
    restaurants: list[dict], radius: float, users: list[dict]
):
    open_and_distance = [r for r in restaurants if r["open_now"] != False]

    filtered = [
        r
        for r in open_and_distance
        if all(cuisine_matches(r, u["cuisines_ranked"]) for u in users)
    ]
    if len(filtered) < 3:
        filtered = open_and_distance

    for r in filtered:
        r["_group_score"] = score_restaurant_for_group(r, users, radius)

    return sorted(filtered, key=lambda r: r["_group_score"], reverse=True)


def get_photo_names(place_id: str, max: int = 3) -> list[str] | None:
    try:
        url = f"https://places.googleapis.com/v1/places/{place_id}"
        headers = {
            "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
            "X-Goog-FieldMask": "photos",
        }

        response = requests.get(url, headers=headers)
        raw = response.json().get("photos", [])
        if not raw:
            return None
        return [p["name"] for p in raw[:max]]
    except Exception:
        logger.exception(f"Get photo names failed for {place_id}")
        return None


def build_photo_media_url(photo_name: str) -> str:
    maxHeightPx = 400
    key = GOOGLE_PLACES_API_KEY
    url = f"https://places.googleapis.com/v1/{photo_name}/media"

    return url + f"?maxHeightPx={maxHeightPx}&key={key}"


@app.get("/photo/{place_id}/{index}")
def get_photo(place_id: str, index: int) -> Response:
    photo_names = get_photo_names(place_id)
    if not photo_names or index >= len(photo_names):
        raise HTTPException(status_code=404, detail="No photo")
    url = build_photo_media_url(photo_names[index])
    raw = requests.get(url)
    media_type = raw.headers["content-type"]

    return Response(content=raw.content, media_type=media_type)


def enrich_reveal_photos(reveal: dict, shortlist: list) -> dict:
    primary = reveal["primary"]
    for s in shortlist:
        if primary["maps_link"] == s["maps_link"] or primary["name"] == s["name"]:
            place_id = primary["maps_link"].split("place_id:")[1]
            photo_names = get_photo_names(place_id)
            if photo_names:
                primary["photo_urls"] = [
                    f"/photo/{place_id}/{i}" for i in range(len(photo_names))
                ]
            break

    for backup in reveal["backups"]:
        for s in shortlist:
            if backup["maps_link"] == s["maps_link"] or backup["name"] == s["name"]:
                place_id = backup["maps_link"].split("place_id:")[1]
                photo_names = get_photo_names(place_id)
                if photo_names:
                    backup["photo_urls"] = [
                        f"/photo/{place_id}/{i}" for i in range(len(photo_names))
                    ]
                break
    return reveal


def run_reveal_pipeline(users: list[dict], latitude: float, longitude: float) -> dict:
    radius = get_search_radius(users)
    restaurants = get_nearby_restaurants(latitude, longitude, 2000)
    shortlist = rank_restaurants_for_group(restaurants, radius, users)
    return generate_reveal(users, shortlist, radius)


def cuisine_matches(restaurant, ranked_cuisines):
    lower_res = [str.lower(s) for s in restaurant["cuisines"]]
    lower_ranked = [str.lower(s) for s in ranked_cuisines]
    for res in lower_ranked:
        if any(res in rc for rc in lower_res):
            return True
    return False


def score_cuisine(restaurant: dict, ranked_cuisines: list[str]) -> int:
    res_cuisines = [str.lower(s) for s in restaurant["cuisines"]]
    ranked_cuisines = [str.lower(s) for s in ranked_cuisines]
    best_match = 0
    points = [10, 7, 5, 3]
    for index, cuisine in enumerate(ranked_cuisines):
        if any(cuisine in rc for rc in res_cuisines):
            best_match = max(best_match, points[min(index, len(points) - 1)])
    return best_match


def score_restaurant_for_person(restaurant: dict, user: dict, radius: float) -> float:
    total = score_cuisine(restaurant, user["cuisines_ranked"])

    if radius > 0:
        total += (radius - restaurant["distance_meters"]) / radius * 5
    total += restaurant["rating"] * 0.5

    return total


def score_restaurant_for_group(
    restaurant: dict, users: list[dict], radius: float
) -> float:
    return min(score_restaurant_for_person(restaurant, user, radius) for user in users)


def _gemini_is_rate_limited(exc: Exception) -> bool:
    if isinstance(exc, (ClientError, ServerError)):
        return exc.code in (429, 503)
    return False


def call_gemini(system_prompt: str, user_prompt: str) -> str:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config={"system_instruction": system_prompt},
            contents=user_prompt,
        )
        return response.text.strip()
    except Exception:
        raise


def call_groq(system_prompt: str, user_prompt: str) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def parse_reveal_response(raw: str) -> dict:
    try:
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        logger.error(f"Failed to parse reveal JSON: {raw}")
        raise


def generate_reveal(users: list[dict], restaurants: list[dict], strict_radius: int):
    restaurants = restaurants[:15]

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
You're part of the group, not an outsider observing them. Only pick from the restaurant's list, don't invent places

Your job:
1. Write a SHORT roast-style personality line for each person based on their food mood
2. Summarise what the group agrees on and where they clash
3. Pick the single best restaurant and hype it up
4. Provide 2 backup options with punchy reasons

Rules for personality lines, agreements, and conflicts (all use the same newline rules):
- Each sentence is at most 10 words (count before writing). Emoji counts as part of that sentence — keep emoji at the END of the sentence, same line.
- A sentence must be complete before you add \\n. NEVER put \\n in the middle of a sentence.
- NEVER put an emoji alone on its own line. NEVER split "text\\n🌶️" or "word\\nrest of sentence".
- Use \\n ONLY between separate complete sentences (each ≤10 words).
- If one sentence is enough, do not add \\n at all.
- Roast-style but friendly for personality lines; roast behaviour, not preferences
- Use deadpan humour, not just exclamation marks
- Talk TO the group directly, not about them

Personality line examples (GOOD — each line is one full sentence):
- "Someone REALLY needs their Thai fix 🌶️"
- "Apparently salads count as a meal 🥗"
- "Would eat anything right now 🤤\\nAbsolutely no standards detected 😌"

Personality line examples (BAD — do not do this):
- "Would eat anything\\nright now 🤤" (splits mid-sentence)
- "Thai fix 🌶️\\n🌶️" (emoji alone on a line)
- "Everyone wants casual vibes and also\\nnobody wants to walk far" (splits one sentence)

Rules for agreements and conflicts:
- Speak as part of the group — use "everyone", "most of us", "almost everyone"
- NEVER say "they both" or "they" — you are IN the group
- Make it fun — emoji at end of sentence, same line
- Example agreements: "Everyone's down for Indian and Mexican 🌶️\\nNobody wants to walk far today 👣"
- Example conflicts: "Half of us want quick bites 🏃\\nThe other half want a vibe 👀"

Rules for primary reason:
- 2 sentences max, hype it up like you're genuinely excited
- Explain why it works for THIS specific group

Rules for backup reasons:
- 1 sentence, punchy

Other rules:
- Respect dietary restrictions strictly, never recommend somewhere a person can't eat
- Never recommend the same restaurant more than once
- The primary must be within the strict tradeoff. Backups may exceed this but should explain the tradeoff in their reason. 
    Example scenario: Restaurant A is the correct cuisine but 500m farther than the agreed distance or Restaurant B is within distance, 
    but it is the the second or third highest rated cuisine instead of first
- Prefer open, highly rated, highly reviewed places
- Return ONLY valid JSON, no explanation, no markdown backticks"""

    user_prompt = f"""Group preferences:
{preferences_text}

Restaurants:
{restaurants_text}

Strict radius:
{strict_radius}

Return this exact JSON structure:
{{
  "personality_lines": {{"name": "one sentence ≤10 words\\noptional second sentence ≤10 words"}},
  "agreements": "sentence one ≤10 words\\nsentence two ≤10 words",
  "conflicts": "sentence one ≤10 words\\nsentence two ≤10 words",
  "primary": {{"name": "...", "reason": "...", "maps_link": "..."}},
  "backups": [{{"name": "...", "reason": "...", "maps_link": "..."}}]
}}"""   

    try:
        raw = call_gemini(system_prompt, user_prompt)
    except (ClientError, ServerError) as e:
        if _gemini_is_rate_limited(e) and GROQ_API_KEY:
            logger.warning(f"Gemini rate limited ({e.code}), falling back to Groq")
            raw = call_groq(system_prompt, user_prompt)
        else:
            raise
    reveal = parse_reveal_response(raw)
    reveal = enrich_reveal_photos(reveal, restaurants)
    return reveal


@app.get("/test-reveal")
def test_reveal():
    """Smoke test for the full reveal pipeline with hardcoded users."""
    if not DEBUG:
        raise HTTPException(status_code=404, detail="Dev endpoint: Not found")
    users = [
        {
            "name": "Chris",
            "hunger": 5,
            "vibe": "quick",
            "cuisines_ranked": ["japanese", "thai"],
            "travel_distance": "short walk (<500m)",
            "dietary": [],
        },
        {
            "name": "Sarah",
            "hunger": 2,
            "vibe": "casual",
            "cuisines_ranked": ["italian", "greek"],
            "travel_distance": "don't mind",
            "dietary": ["vegetarian"],
        },
    ]
    return run_reveal_pipeline(users, -37.8136, 144.9631)


def geocode_location(address: str) -> tuple[float, float]:
    """
    Convert a text address to (latitude, longitude) via Geocoding API v4.

    v4 puts the address in the URL path and authenticates with X-Goog-Api-Key
    (same header style as Places API). Coords live at results[0].location.
    """
    if not address or not address.strip():
        raise ValueError("Address is required")

    url = f"https://geocode.googleapis.com/v4/geocode/address/{quote(address)}"
    response = requests.get(url, headers={"X-Goog-Api-Key": GOOGLE_PLACES_API_KEY})
    data = response.json()
    results = data.get("results", [])
    if not results:
        raise ValueError(f"No geocoding results for: {address}")

    location = results[0]["location"]
    return location["latitude"], location["longitude"]


@app.get("/test-geocode")
def test_geocode(address: str = "Federation Square, Melbourne"):
    if not DEBUG:
        raise HTTPException(status_code=404, detail="Dev endpoint: Not found")
    lat, lng = geocode_location(address)
    return {"address": address, "latitude": lat, "longitude": lng}