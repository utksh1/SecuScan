import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import Request
from .request_context import set_request_id

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # Accept existing X-Request-ID or generate one
        request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(request_id)

        # Make available during request lifecycle
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled exception in RequestIDMiddleware")
            response = Response("Internal Server Error", status_code=500)

        # Return ID in response headers
        response.headers["X-Request-ID"] = request_id

        return response