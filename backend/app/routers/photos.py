import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app import config
from app import errors
from app.limiter import limiter
from app.services import photos

router = APIRouter()


@router.get("/photo/{place_id}/{index}")
@limiter.limit("30/minute")
def get_photo(request: Request, place_id: str, index: int) -> Response:
    """
    Proxy a Google Places photo as raw image bytes.

    Args:
        place_id: Google Places place ID.
        index: Zero-based index into the place's photo list.

    Returns:
        FastAPI Response with the image content-type from Google.

    Raises:
        HTTPException: 404 when the photo index is missing.
        HTTPException: 502/503/504 when upstream photo fetch fails.
    """
    try:
        photo_names = photos.get_photo_names(place_id, strict=True)

        if not photo_names or index >= len(photo_names):
            raise HTTPException(404, "No photo")

        url = photos.build_photo_media_url(photo_names[index])
        try:
            raw = requests.get(url, timeout=errors.UPSTREAM_TIMEOUT_SEC)
        except requests.Timeout as e:
            config.logger.exception(f"Photo media timed out for {place_id}")
            raise errors.UpstreamTimeout(f"Photo media timed out for {place_id}") from e
        except requests.ConnectionError as e:
            config.logger.exception(f"Photo media unavailable for {place_id}")
            raise errors.UpstreamUnavailable(f"Photo media unavailable for {place_id}") from e

        if raw.status_code != 200:
            config.logger.error(f"Photo media status={raw.status_code}")
            raise errors.UpstreamBadResponse(f"Photo media status={raw.status_code}")
        media_type = raw.headers["content-type"]
        return Response(content=raw.content, media_type=media_type)
    except errors.UpstreamError as e:
        raise errors.upstream_to_http(e)
