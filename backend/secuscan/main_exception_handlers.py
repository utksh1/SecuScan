"""
Exception handlers extracted from backend/secuscan/main.py for isolated unit testing.

These handlers are registered on the FastAPI app in main.py.  They are extracted
into this small import-safe module so they can be unit-tested directly without
pulling in the full main.py import chain (FastAPI app, routes, database, etc.).
main.py re-exports these so the app registration is unchanged.
"""

from __future__ import annotations

import traceback
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)

from .rate_limiter import RateLimitExceeded
from .request_context import get_request_id


# Cache the settings reference so this module does not import settings at module
# load time (settings imports pydantic which may not be installed in all test
# environments).  The actual settings value is set when the handler is called.
_settings = None


def _get_settings() -> Any:
    """Lazily import settings to avoid import-time pydantic dependency."""
    global _settings
    if _settings is None:
        from .config import settings

        _settings = settings
    return _settings


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for RateLimitExceeded errors.
    Returns a consistent JSON 429 response matching the API's error schema.
    """
    retry_after = getattr(exc, "retry_after", 60)
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

    Merges headers from the original exception (e.g. X-RateLimit-Limit,
    X-RateLimit-Remaining, Retry-After) with default headers, so callers
    always receive accurate rate-limit metadata.
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


async def custom_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Wraps the default HTTP exception handler and adds an X-Request-ID header
    to all HTTP exception responses.
    """
    response = await http_exception_handler(request, exc)
    response.headers["X-Request-ID"] = getattr(
        request.state, "request_id", get_request_id()
    )
    return response


async def custom_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Wraps the default validation exception handler and adds an X-Request-ID header.
    """
    response = await request_validation_exception_handler(request, exc)
    response.headers["X-Request-ID"] = getattr(
        request.state, "request_id", get_request_id()
    )
    return response


async def custom_unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse | PlainTextResponse:
    """
    Top-level uncaught exception handler.
    Returns detailed HTML in debug mode and a plain-text 500 otherwise.
    Both response types include X-Request-ID.
    """
    settings = _get_settings()
    request_id = getattr(request.state, "request_id", get_request_id())
    if settings.debug:
        html = (
            "<html><body>"
            f"<h1>500 Internal Server Error</h1>"
            f"<pre>{traceback.format_exc()}</pre>"
            "</body></html>"
        )
        response = HTMLResponse(html, status_code=500)
    else:
        response = PlainTextResponse("Internal Server Error", status_code=500)
    response.headers["X-Request-ID"] = request_id
    return response
