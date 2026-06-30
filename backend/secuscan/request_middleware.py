from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
import logging
from .request_context import set_request_id
from .config import settings

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # Accept existing X-Request-ID or generate one
        request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(request_id)

        # Make available during request lifecycle
        request.state.request_id = request_id

        response = await call_next(request)

        # Return ID in response headers
        response.headers["X-Request-ID"] = request_id

        return response


class HardenCORSMiddleware(BaseHTTPMiddleware):
    """
    Harden CORS by validating Origin headers against the allowed origins
    when present. Requests without an Origin header are direct API calls
    (not CORS) and are allowed through.
    """
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        if not origin:
            return await call_next(request)

        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)

        allowed = settings.cors_allowed_origins
        if origin in allowed or "*" in allowed:
            return await call_next(request)

        logger.warning(f"⚠️ [CORS] Rejected cross-origin request from {origin}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"Not allowed by CORS: Origin '{origin}' is not permitted"
            },
            status_code=403
        )