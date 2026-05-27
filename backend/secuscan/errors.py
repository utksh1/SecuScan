"""
Standardized machine-readable error responses for SecuScan API.
Implements RFC 7807-style problem details with extra fields.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


def _new_request_id() -> str:
    return str(uuid.uuid4())


def problem(
    *,
    status: int,
    code: str,
    message: str,
    field: Optional[str] = None,
    request_id: Optional[str] = None,
    hint: Optional[str] = None,
    details: Optional[Any] = None,
) -> dict:
    """Build a standardized error payload."""
    body: dict = {
        "code": code,
        "message": message,
        "request_id": request_id or _new_request_id(),
        "status": status,
    }
    if field is not None:
        body["field"] = field
    if hint is not None:
        body["hint"] = hint
    if details is not None:
        body["details"] = details
    return body


# ── Exception handlers ────────────────────────────────────────────────────────

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert HTTPException into a problem-details response."""
    rid = getattr(request.state, "request_id", _new_request_id())

    # Map status → (code, hint)
    _MAP = {
        400: ("BAD_REQUEST",        "Check the request body and query parameters."),
        401: ("UNAUTHORIZED",       "Provide a valid Bearer token in the Authorization header."),
        403: ("FORBIDDEN",          "You do not have permission to perform this action."),
        404: ("NOT_FOUND",          "Verify the resource identifier and try again."),
        409: ("CONFLICT",           "A resource with conflicting properties already exists."),
        422: ("UNPROCESSABLE",      "The payload was well-formed but failed semantic validation."),
        429: ("RATE_LIMITED",       "Wait before retrying. Check Retry-After header if present."),
        500: ("INTERNAL_ERROR",     "An unexpected server error occurred. Please try again later."),
        503: ("SERVICE_UNAVAILABLE","The server is temporarily unable to handle the request."),
    }
    code, hint = _MAP.get(exc.status_code, ("ERROR", None))

    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", str(detail))
        code    = detail.get("code", code)
        hint    = detail.get("hint", hint)
        field   = detail.get("field")
    else:
        message = str(detail) if detail else "An error occurred."
        field   = None

    return JSONResponse(
        status_code=exc.status_code,
        content=problem(
            status=exc.status_code,
            code=code,
            message=message,
            field=field,
            request_id=rid,
            hint=hint,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic validation errors into problem-details responses."""
    rid = getattr(request.state, "request_id", _new_request_id())

    errors = exc.errors()
    first  = errors[0] if errors else {}
    field  = ".".join(str(p) for p in first.get("loc", [])) or None
    msg    = first.get("msg", "Validation error.")

    return JSONResponse(
        status_code=422,
        content=problem(
            status=422,
            code="VALIDATION_ERROR",
            message=msg,
            field=field,
            request_id=rid,
            hint="Review the request schema and correct the highlighted field.",
            details=[
                {
                    "field": ".".join(str(p) for p in e.get("loc", [])),
                    "message": e.get("msg"),
                    "type": e.get("type"),
                }
                for e in errors
            ],
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected server errors."""
    rid = getattr(request.state, "request_id", _new_request_id())
    return JSONResponse(
        status_code=500,
        content=problem(
            status=500,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            request_id=rid,
            hint="If the problem persists, contact support with the request_id.",
        ),
    )