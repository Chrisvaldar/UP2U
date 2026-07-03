from fastapi import HTTPException

UPSTREAM_TIMEOUT_SEC = 10


class UpstreamError(Exception):
    pass


class UpstreamTimeout(UpstreamError):
    pass


class UpstreamUnavailable(UpstreamError):
    pass


class UpstreamBadResponse(UpstreamError):
    pass


def upstream_to_http(exc: UpstreamError) -> HTTPException:
    if isinstance(exc, UpstreamTimeout):
        return HTTPException(
            status_code=504, detail="The request took too long. Try again."
        )
    elif isinstance(exc, UpstreamUnavailable):
        return HTTPException(
            status_code=503, detail="Service is temporarily unavailable. Try again."
        )
    elif isinstance(exc, UpstreamBadResponse):
        return HTTPException(
            status_code=502,
            detail="Something went wrong processing that request. Try again.",
        )
    else:
        return HTTPException(status_code=502, detail="Unexpected upstream error.")
