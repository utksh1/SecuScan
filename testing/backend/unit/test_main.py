"""
Unit tests for backend/secuscan/main_exception_handlers.py exception handlers.

Covers the standalone exception handler and redirect functions extracted from
main.py to enable safe unit testing without the full FastAPI app initialization.
"""

from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
import pytest

from backend.secuscan.main_exception_handlers import (
    redirect_api_docs,
    redirect_api_redoc,
    redirect_api_openapi,
    rate_limit_exceeded_handler,
    generic_rate_limit_handler,
    custom_http_exception_handler,
    custom_validation_exception_handler,
    custom_unhandled_exception_handler,
)
from backend.secuscan.main_exception_handlers import RateLimitExceeded


# ---------------------------------------------------------------------------
# Redirect endpoints
# ---------------------------------------------------------------------------


class TestRedirectEndpoints:
    @pytest.mark.asyncio
    async def test_redirect_api_docs_returns_307_to_docs(self):
        result = await redirect_api_docs()
        assert result.status_code == 307
        assert result.headers["location"] == "/docs"

    @pytest.mark.asyncio
    async def test_redirect_api_redoc_returns_307_to_redoc(self):
        result = await redirect_api_redoc()
        assert result.status_code == 307
        assert result.headers["location"] == "/redoc"

    @pytest.mark.asyncio
    async def test_redirect_api_openapi_returns_307_to_openapi(self):
        result = await redirect_api_openapi()
        assert result.status_code == 307
        assert result.headers["location"] == "/openapi.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_request(mock_request_id: str | None = None) -> Request:
    """Build a mock Request with a state.request_id attribute."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
    }
    request = Request(scope, receive=MagicMock())
    if mock_request_id is not None:
        request.state.request_id = mock_request_id
    return request


# ---------------------------------------------------------------------------
# rate_limit_exceeded_handler
# ---------------------------------------------------------------------------


class TestRateLimitExceededHandler:
    @pytest.mark.asyncio
    async def test_returns_429_status(self):
        exc = RateLimitExceeded(detail="Too many requests")
        request = make_request("req-123")
        response = await rate_limit_exceeded_handler(request, exc)
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_body_contains_error_message(self):
        exc = RateLimitExceeded(detail="Rate limit exceeded for IP 1.2.3.4")
        request = make_request("req-123")
        response = await rate_limit_exceeded_handler(request, exc)
        body = response.body.decode()
        assert "Rate limit exceeded" in body
        assert "retry_after" in body

    @pytest.mark.asyncio
    async def test_retry_after_header_set(self):
        exc = RateLimitExceeded(detail="Limit reached", retry_after=120)
        request = make_request("req-456")
        response = await rate_limit_exceeded_handler(request, exc)
        assert response.headers["retry-after"] == "120"

    @pytest.mark.asyncio
    async def test_default_retry_after_is_60(self):
        exc = RateLimitExceeded(detail="Limit reached")
        request = make_request()
        response = await rate_limit_exceeded_handler(request, exc)
        assert response.headers["retry-after"] == "60"

    @pytest.mark.asyncio
    async def test_x_request_id_header_added(self):
        exc = RateLimitExceeded(detail="Limit reached")
        request = make_request("my-request-id")
        response = await rate_limit_exceeded_handler(request, exc)
        assert response.headers["x-request-id"] == "my-request-id"

    @pytest.mark.asyncio
    async def test_exc_with_detail_attribute(self):
        exc = RateLimitExceeded(detail="Custom rate limit message")
        request = make_request("req-789")
        response = await rate_limit_exceeded_handler(request, exc)
        body = response.body.decode()
        assert "Custom rate limit message" in body


# ---------------------------------------------------------------------------
# generic_rate_limit_handler
# ---------------------------------------------------------------------------


class TestGenericRateLimitHandler:
    @pytest.mark.asyncio
    async def test_returns_429_status(self):
        exc = Exception("429-like exception")
        request = make_request("req-1")
        response = await generic_rate_limit_handler(request, exc)
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_body_contains_too_many_requests(self):
        exc = Exception("rate limit")
        request = make_request("req-2")
        response = await generic_rate_limit_handler(request, exc)
        body = response.body.decode()
        assert "Too Many Requests" in body

    @pytest.mark.asyncio
    async def test_retry_after_defaults_to_60(self):
        exc = Exception("rate limit")
        request = make_request()
        response = await generic_rate_limit_handler(request, exc)
        assert response.headers["retry-after"] == "60"

    @pytest.mark.asyncio
    async def test_existing_retry_after_preserved(self):
        exc = Exception("rate limit")
        exc.headers = {"Retry-After": "300", "X-Custom": "val"}
        request = make_request("req-3")
        response = await generic_rate_limit_handler(request, exc)
        assert response.headers["retry-after"] == "300"
        assert response.headers["x-custom"] == "val"

    @pytest.mark.asyncio
    async def test_x_request_id_header_added(self):
        exc = Exception("rate limit")
        request = make_request("xid-abc")
        response = await generic_rate_limit_handler(request, exc)
        assert response.headers["x-request-id"] == "xid-abc"


# ---------------------------------------------------------------------------
# custom_http_exception_handler
# ---------------------------------------------------------------------------


class TestCustomHttpExceptionHandler:
    @pytest.mark.asyncio
    async def test_adds_x_request_id_header(self):
        exc = StarletteHTTPException(status_code=404, detail="Not found")
        request = make_request("http-exc-1")
        response = await custom_http_exception_handler(request, exc)
        assert response.status_code == 404
        assert response.headers["x-request-id"] == "http-exc-1"

    @pytest.mark.asyncio
    async def test_propagates_original_status_code(self):
        exc = StarletteHTTPException(status_code=403, detail="Forbidden")
        request = make_request()
        response = await custom_http_exception_handler(request, exc)
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# custom_validation_exception_handler
# ---------------------------------------------------------------------------


class TestCustomValidationExceptionHandler:
    @pytest.mark.asyncio
    async def test_adds_x_request_id_header(self):
        errors = [{"loc": ("body",), "msg": "field required", "type": "missing"}]
        exc = RequestValidationError(errors)
        request = make_request("val-exc-1")
        response = await custom_validation_exception_handler(request, exc)
        assert response.status_code == 422
        assert response.headers["x-request-id"] == "val-exc-1"

    @pytest.mark.asyncio
    async def test_returns_422_for_validation_errors(self):
        errors = []
        exc = RequestValidationError(errors)
        request = make_request()
        response = await custom_validation_exception_handler(request, exc)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# custom_unhandled_exception_handler
# ---------------------------------------------------------------------------


class TestCustomUnhandledExceptionHandler:
    @pytest.mark.asyncio
    async def test_returns_500_status(self):
        exc = RuntimeError("unexpected error")
        request = make_request("unhandled-1")
        response = await custom_unhandled_exception_handler(request, exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_plain_text_body_in_production(self):
        exc = ValueError("bad value")
        request = make_request("unhandled-2")
        # settings is imported inside the function, so patch the source
        from backend.secuscan import config as config_module
        original = config_module.settings
        config_module.settings = MagicMock(debug=False)
        try:
            response = await custom_unhandled_exception_handler(request, exc)
            assert response.status_code == 500
            body = response.body.decode()
            assert "Internal Server Error" in body
            # Should be plain text, not HTML
            assert "<html>" not in body
        finally:
            config_module.settings = original

    @pytest.mark.asyncio
    async def test_debug_mode_returns_html(self):
        exc = ValueError("bad value")
        request = make_request("unhandled-3")
        from backend.secuscan import config as config_module
        original = config_module.settings
        config_module.settings = MagicMock(debug=True)
        try:
            response = await custom_unhandled_exception_handler(request, exc)
            assert response.status_code == 500
            body = response.body.decode()
            assert "<html>" in body
            # In debug mode, the response is HTML, not plain text
            assert "<pre>" in body
        finally:
            config_module.settings = original

    @pytest.mark.asyncio
    async def test_x_request_id_header_added(self):
        exc = RuntimeError("unexpected")
        request = make_request("unhandled-xid")
        from backend.secuscan import config as config_module
        original = config_module.settings
        config_module.settings = MagicMock(debug=False)
        try:
            response = await custom_unhandled_exception_handler(request, exc)
            assert response.headers["x-request-id"] == "unhandled-xid"
        finally:
            config_module.settings = original
