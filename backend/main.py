from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
import os
import redis
import random, string
import json
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

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
                "cuisines": [t for t in types if t not in GENERIC_TYPES],
                "summary": place.get("editorialSummary", {}).get("text", ""),
                "open_now": place.get("regularOpeningHours", {}).get("openNow", None),
                "maps_link": f"https://www.google.com/maps/place/?q=place_id:{place.get('id', '')}",
            }
        )
    return cleaned


def get_nearby_restaurants(latitude: float, longitude: float):
    url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.priceLevel,places.formattedAddress,places.types,places.regularOpeningHours,places.editorialSummary,places.id",
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
