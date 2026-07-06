"""
Exception handlers and redirect endpoints for main.py.

Extracted into a standalone import-safe module so they can be unit-tested
without pulling in the heavy FastAPI app initialization chain.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

# RateLimitExceeded is a simple HTTPException subclass — define locally to avoid
# pulling in the full rate_limiter module (which requires redis at import time).
from starlette.exceptions import HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


class RateLimitExceeded(HTTPException):
    """Raised when a rate limit is exceeded. Caught by a global exception handler."""

    def __init__(self, detail: str = None, retry_after: int = None):
        super().__init__(status_code=HTTP_429_TOO_MANY_REQUESTS, detail=detail)
        self.retry_after = retry_after
from .request_context import get_request_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Redirect endpoints
# ---------------------------------------------------------------------------


async def redirect_api_docs():
    return RedirectResponse(url="/docs")


async def redirect_api_redoc():
    return RedirectResponse(url="/redoc")


async def redirect_api_openapi():
    return RedirectResponse(url="/openapi.json")


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    Returns a consistent JSON 429 response matching the API's error schema.
    """
    logger.warning(
        "Rate limit exceeded for %s on %s - %s",
        request.client.host if request.client else "unknown",
        request.url.path,
        str(exc),
    )
    retry_after = getattr(exc, "retry_after", None) or 60
    return JSONResponse(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": str(exc.detail) if hasattr(exc, "detail") else "Too Many Requests",
            "retry_after": retry_after,
            "message": "Rate limit exceeded. Please wait before making more requests.",
        },
        headers={
            "Retry-After": str(retry_after),
            "X-Request-ID": getattr(request.state, "request_id", get_request_id()),
        },
    )


async def generic_rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Generic handler for 429 status code exceptions.
    Merges headers from the original exception with default headers.
    """
    exc_headers = getattr(exc, "headers", None) or {}
    headers = {
        "X-Request-ID": getattr(request.state, "request_id", get_request_id()),
        **exc_headers,
    }
    if "Retry-After" not in headers:
        headers["Retry-After"] = "60"
    return JSONResponse(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please try again later.",
        },
        headers=headers,
    )


async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Catches StarletteHTTPException and adds X-Request-ID to the response.
    """
    from fastapi.exception_handlers import http_exception_handler

    response = await http_exception_handler(request, exc)
    response.headers["X-Request-ID"] = getattr(request.state, "request_id", get_request_id())
    return response


async def custom_validation_exception_handler(request: Request, exc):
    """
    Catches RequestValidationError and adds X-Request-ID to the response.
    """
    from fastapi.exception_handlers import request_validation_exception_handler
    from fastapi.exceptions import RequestValidationError

    response = await request_validation_exception_handler(request, exc)
    response.headers["X-Request-ID"] = getattr(request.state, "request_id", get_request_id())
    return response


async def custom_unhandled_exception_handler(request: Request, exc: Exception) -> HTMLResponse | PlainTextResponse:
    """
    Catches unhandled exceptions and returns either a debug traceback (in debug mode)
    or a generic 500 error.
    """
    logger.exception("Unhandled exception in request lifecycle")
    from .config import settings

    if settings.debug:
        html = (
            "<html><body><h1>500 Internal Server Error</h1>"
            f"<pre>{traceback.format_exc()}</pre></body></html>"
        )
        response = HTMLResponse(html, status_code=500)
    else:
        response = PlainTextResponse("Internal Server Error", status_code=500)
    response.headers["X-Request-ID"] = getattr(request.state, "request_id", get_request_id())
    return response
