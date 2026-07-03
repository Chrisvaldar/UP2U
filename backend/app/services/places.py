import math
import requests
from collections import defaultdict

from app import config
from app import errors
from app import utils

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
        "X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY,
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
    try:
        response = requests.post(
            url, headers=headers, json=body, timeout=errors.UPSTREAM_TIMEOUT_SEC
        )
    except requests.Timeout as e:
        raise errors.UpstreamTimeout("places searchNearby timed out") from e
    except requests.ConnectionError as e:
        raise errors.UpstreamUnavailable("places searchNearby unreachable") from e
    if response.status_code != 200:
        config.logger.error(
            f"Getting restaurants failed with code {response.status_code} and body: {utils.truncate_log(response.text)}"
        )
        raise errors.UpstreamBadResponse(f"places searchNearby status={response.status_code}")
    raw = response.json().get("places", [])
    restaurants = clean_restaurants(raw, latitude, longitude)
    return restaurants
