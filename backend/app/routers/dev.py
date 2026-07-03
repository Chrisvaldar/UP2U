from fastapi import APIRouter, HTTPException

from app import config
from app import errors
from app.services import ai_reveal
from app.services import geocoding
from app.services import places

router = APIRouter()


@router.get("/test-places")
def test_places(radius: float = 500):
    if not config.DEBUG:
        raise HTTPException(status_code=404, detail="Dev endpoint: Not found")
    try:
        return places.get_nearby_restaurants(-37.8136, 144.9631, radius)
    except errors.UpstreamError as e:
        raise errors.upstream_to_http(e)


@router.get("/test-reveal")
def test_reveal():
    """Smoke test for the full reveal pipeline with hardcoded users."""
    if not config.DEBUG:
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
    try:
        return ai_reveal.run_reveal_pipeline(users, -37.8136, 144.9631)
    except errors.UpstreamError as e:
        raise errors.upstream_to_http(e)


@router.get("/test-geocode")
def test_geocode(address: str = "Federation Square, Melbourne"):
    if not config.DEBUG:
        raise HTTPException(status_code=404, detail="Dev endpoint: Not found")
    try:
        lat, lng = geocoding.geocode_location(address)
    except errors.UpstreamError as e:
        raise errors.upstream_to_http(e)
    except ValueError:
        raise HTTPException(status_code=404, detail="No geocoding results for that address.")
    return {"address": address, "latitude": lat, "longitude": lng}
