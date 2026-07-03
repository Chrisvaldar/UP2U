import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app import config
from app import errors
from app.services import photos

router = APIRouter()


@router.get("/photo/{place_id}/{index}")
def get_photo(place_id: str, index: int) -> Response:
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
