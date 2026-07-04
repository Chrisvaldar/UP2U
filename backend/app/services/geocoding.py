from urllib.parse import quote
import requests

from app import config
from app import errors


def geocode_location(address: str) -> tuple[float, float]:
    """
    Convert a text address to latitude and longitude via Geocoding API v4.

    Args:
        address: Free-text address to geocode.

    Returns:
        A (latitude, longitude) tuple from the first geocoding result.

    Raises:
        ValueError: If the address is empty or no results are returned.
        UpstreamTimeout: If the geocoding request times out.
        UpstreamUnavailable: If the geocoding service is unreachable.
        UpstreamBadResponse: If the API returns a non-200 status code.
    """
    if not address or not address.strip():
        raise ValueError("Address is required")

    url = f"https://geocode.googleapis.com/v4/geocode/address/{quote(address)}"
    try:
        response = requests.get(
            url,
            headers={"X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY},
            timeout=errors.UPSTREAM_TIMEOUT_SEC,
        )
    except requests.Timeout as e:
        raise errors.UpstreamTimeout("geocode address timed out") from e
    except requests.ConnectionError as e:
        raise errors.UpstreamUnavailable("geocode address unreachable") from e

    if response.status_code != 200:
        config.logger.error(f"Geocode failed with code {response.status_code}")
        raise errors.UpstreamBadResponse(f"geocode status={response.status_code}")

    data = response.json()
    results = data.get("results", [])
    if not results:
        raise ValueError(f"No geocoding results for: {address}")

    location = results[0]["location"]
    return location["latitude"], location["longitude"]
