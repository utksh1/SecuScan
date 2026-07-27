"""Tests for main.py exception handler functions."""

import pytest
import json

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.secuscan.main import (
    rate_limit_exceeded_handler,
    generic_rate_limit_handler,
    custom_http_exception_handler,
    custom_validation_exception_handler,
    custom_unhandled_exception_handler,
    RateLimitExceeded,
)


def _make_request(path: str = "/test") -> Request:
    return Request(scope={"type": "http", "method": "GET", "path": path, "headers": []})


def _parse_json(response) -> dict:
    body = response.body
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    return json.loads(body)


class TestRateLimitExceededHandler:
    """rate_limit_exceeded_handler must return a consistent JSON 429 response."""

    @pytest.mark.asyncio
    async def test_returns_429_status(self):
        exc = RateLimitExceeded(status_code=429, detail="slow down")
        response = await rate_limit_exceeded_handler(_make_request(), exc)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_returns_json_with_error_field(self):
        exc = RateLimitExceeded(status_code=429, detail="slow down")
        response = await rate_limit_exceeded_handler(_make_request(), exc)
        body = _parse_json(response)
        assert "error" in body

    @pytest.mark.asyncio
    async def test_returns_json_with_retry_after_field(self):
        exc = RateLimitExceeded(status_code=429, detail="slow down")
        response = await rate_limit_exceeded_handler(_make_request(), exc)
        body = _parse_json(response)
        assert "retry_after" in body

    @pytest.mark.asyncio
    async def test_returns_json_with_message_field(self):
        exc = RateLimitExceeded(status_code=429, detail="slow down")
        response = await rate_limit_exceeded_handler(_make_request(), exc)
        body = _parse_json(response)
        assert "message" in body

    @pytest.mark.asyncio
    async def test_includes_retry_after_header(self):
        exc = RateLimitExceeded(status_code=429, detail="slow down")
        response = await rate_limit_exceeded_handler(_make_request(), exc)
        header_keys = {k.lower() for k in response.headers}
        assert "retry-after" in header_keys


class TestGenericRateLimitHandler:
    """generic_rate_limit_handler must return a consistent JSON 429 response."""

    @pytest.mark.asyncio
    async def test_returns_429_status(self):
        exc = StarletteHTTPException(status_code=429, detail="rate limit")
        response = await generic_rate_limit_handler(_make_request(), exc)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_returns_json_with_error_and_message(self):
        exc = StarletteHTTPException(status_code=429, detail="rate limit")
        response = await generic_rate_limit_handler(_make_request(), exc)
        body = _parse_json(response)
        assert "error" in body
        assert "message" in body


class TestCustomHTTPExceptionHandler:
    """custom_http_exception_handler must add X-Request-ID to the response."""

    @pytest.mark.asyncio
    async def test_passes_through_original_status_code(self):
        exc = StarletteHTTPException(status_code=404, detail="not found")
        response = await custom_http_exception_handler(_make_request(), exc)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_adds_request_id_header(self):
        exc = StarletteHTTPException(status_code=404, detail="not found")
        response = await custom_http_exception_handler(_make_request(), exc)
        assert "x-request-id" in {k.lower() for k in response.headers}


class TestCustomValidationExceptionHandler:
    """custom_validation_exception_handler must return 422 with X-Request-ID."""

    @pytest.mark.asyncio
    async def test_returns_422_for_validation_errors(self):
        exc = RequestValidationError(errors=[])
        response = await custom_validation_exception_handler(_make_request(), exc)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_adds_request_id_header(self):
        exc = RequestValidationError(errors=[])
        response = await custom_validation_exception_handler(_make_request(), exc)
        assert "x-request-id" in {k.lower() for k in response.headers}


class TestCustomUnhandledExceptionHandler:
    """custom_unhandled_exception_handler must return 500 consistently."""

    @pytest.mark.asyncio
    async def test_returns_500_for_unhandled_exceptions(self):
        exc = ValueError("unexpected value")
        response = await custom_unhandled_exception_handler(_make_request(), exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_adds_request_id_header(self):
        exc = RuntimeError("something bad happened")
        response = await custom_unhandled_exception_handler(_make_request(), exc)
        assert "x-request-id" in {k.lower() for k in response.headers}
