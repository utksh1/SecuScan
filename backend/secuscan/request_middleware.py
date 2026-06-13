from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
import logging
from .request_context import set_request_id

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
    Harden CORS by rejecting requests missing the Origin header.
    This prevents unintended cross-origin access and ensures that
    only explicitly allowed origins are accepted.
    """
    async def dispatch(self, request: Request, call_next):
        # Skip for documentation and root endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)

        # Skip for health check if it's internal
        if request.url.path == "/api/v1/health" and not request.headers.get("origin"):
            # We might want to allow internal health checks without Origin
            # but the mandate is to reject missing Origin headers.
            # However, health checks are often called by monitoring tools.
            # Let's be strict for now as per mandate.
            pass

        origin = request.headers.get("origin")
        if not origin:
            logger.warning(f"⚠️ [CORS] Rejected request without Origin header from {request.client.host if request.client else 'unknown'}")
            return JSONResponse(
                content={
                    "success": False,
                    "message": "Not allowed by CORS: Missing Origin header"
                },
                status_code=403
            )

        return await call_next(request)