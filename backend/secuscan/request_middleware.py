from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from .request_context import set_request_id


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