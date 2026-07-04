import requests

from app import config
from app import errors


def get_photo_names(place_id: str, max: int = 3, strict=False) -> list[str] | None:
    """
    Fetch photo resource names for a Google Places place ID.

    Args:
        place_id: Google Places place ID.
        max: Maximum number of photo names to return. Defaults to 3.
        strict: When True, re-raise upstream errors instead of returning None.

    Returns:
        A list of photo resource name strings, or None on failure or when no
        photos exist.

    Raises:
        UpstreamTimeout: When strict is True and the request times out.
        UpstreamUnavailable: When strict is True and the service is unreachable.
        UpstreamBadResponse: When strict is True and the response is invalid.
    """
    try:
        url = f"https://places.googleapis.com/v1/places/{place_id}"
        headers = {
            "X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY,
            "X-Goog-FieldMask": "photos",
        }

        response = requests.get(url, headers=headers, timeout=errors.UPSTREAM_TIMEOUT_SEC)

        if response.status_code != 200:
            raise errors.UpstreamBadResponse(f"Get photos status={response.status_code}")

        raw = response.json().get("photos", [])
        if not raw:
            return None
        return [p["name"] for p in raw[:max]]
    except requests.Timeout:
        exc = errors.UpstreamTimeout(f"Get photos timed out for {place_id}")
        config.logger.exception(f"Get photos timed out for {place_id}")
    except requests.ConnectionError:
        exc = errors.UpstreamUnavailable(f"Get photos unavailable for {place_id}")
        config.logger.exception(f"Get photos unavailable for {place_id}")
    except (errors.UpstreamBadResponse, KeyError, TypeError) as e:
        exc = (
            e
            if isinstance(e, errors.UpstreamBadResponse)
            else errors.UpstreamBadResponse(f"Get photos malformed response")
        )
        config.logger.exception(f"Get photos malformed response")
    if strict:
        raise exc
    return None


def build_photo_media_url(photo_name: str) -> str:
    """
    Build a Google Places photo media URL for direct image fetch.

    Args:
        photo_name: Photo resource name from get_photo_names.

    Returns:
        A media URL with maxHeightPx=400 and the Places API key appended.
    """
    maxHeightPx = 400
    key = config.GOOGLE_PLACES_API_KEY
    url = f"https://places.googleapis.com/v1/{photo_name}/media"

    return url + f"?maxHeightPx={maxHeightPx}&key={key}"


def enrich_reveal_photos(reveal: dict, shortlist: list) -> dict:
    """
    Attach proxied photo URLs to the primary and backup restaurants in a reveal.

    Args:
        reveal: Parsed AI reveal dict with primary and backups entries.
        shortlist: Ranked restaurant shortlist used to resolve place IDs.

    Returns:
        The same reveal dict with photo_urls added as /photo/{place_id}/{index}
        paths when photos are available.
    """
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
