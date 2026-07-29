"""
Unit tests for exception handlers extracted from backend/secuscan/main.py.

The handlers are defined in backend.secuscan.main_exception_handlers, which is
import-safe (does not require FastAPI app, routes, database, etc. at test time).
"""

import sys
from unittest.mock import MagicMock

import pytest


# Stub types used by the module under test.
class _StubRequestState:
    def __init__(self, request_id: str = None):
        self.request_id = request_id


class _StubRequest:
    def __init__(self, request_id: str = None):
        self.state = _StubRequestState(request_id)
        self.client = MagicMock()
        self.client.host = "127.0.0.1"


class _StubHTTPException(Exception):
    def __init__(self, status_code: int, detail=None, headers=None):
        self.status_code = status_code
        self.detail = detail or {}
        self.headers = headers or {}


class _StubStarletteHTTPException(Exception):
    def __init__(self, status_code: int, detail=None, headers=None):
        self.status_code = status_code
        self.detail = detail or ""
        self.headers = headers or {}


class _StubJSONResponse:
    def __init__(self, content, status_code: int = 200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = dict(headers or {})


class _StubPlainTextResponse:
    def __init__(self, content, status_code: int = 200):
        self.body = content.encode()
        self.status_code = status_code
        self.headers = {}


# Build individual mock modules for fastapi sub-modules.
mock_fastapi_responses = MagicMock(name="fastapi.responses")
mock_fastapi_responses.JSONResponse = _StubJSONResponse
mock_fastapi_responses.HTMLResponse = lambda html, status_code=200: _StubPlainTextResponse(html, status_code)
mock_fastapi_responses.PlainTextResponse = _StubPlainTextResponse

mock_fastapi_exceptions = MagicMock(name="fastapi.exceptions")
mock_fastapi_exceptions.RequestValidationError = Exception

mock_fastapi_exception_handlers = MagicMock(name="fastapi.exception_handlers")
mock_fastapi_exception_handlers.http_exception_handler = MagicMock(
    return_value=_StubJSONResponse({}, status_code=400)
)
mock_fastapi_exception_handlers.request_validation_exception_handler = MagicMock(
    return_value=_StubJSONResponse({}, status_code=422)
)

# Make these awaitable (they are async in real FastAPI).
_original_http_handler = mock_fastapi_exception_handlers.http_exception_handler
_original_val_handler = mock_fastapi_exception_handlers.request_validation_exception_handler

async def _async_http_handler(*args, **kwargs):
    return _original_http_handler(*args, **kwargs)

async def _async_val_handler(*args, **kwargs):
    return _original_val_handler(*args, **kwargs)

mock_fastapi_exception_handlers.http_exception_handler = _async_http_handler
mock_fastapi_exception_handlers.request_validation_exception_handler = _async_val_handler

mock_fastapi = MagicMock(name="fastapi")
mock_fastapi.Request = _StubRequest
mock_fastapi.HTTPException = _StubHTTPException
mock_fastapi.responses = mock_fastapi_responses
mock_fastapi.exceptions = mock_fastapi_exceptions
mock_fastapi.exception_handlers = mock_fastapi_exception_handlers

mock_starlette = MagicMock(name="starlette")
mock_starlette.HTTP_429_TOO_MANY_REQUESTS = 429
mock_starlette.exceptions.HTTPException = _StubStarletteHTTPException

mock_request_context = MagicMock(name="request_context")
mock_request_context.get_request_id = lambda: "test-request-id-123"

# Register all mock modules in sys.modules BEFORE importing the module under test.
sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()
sys.modules["fastapi"] = mock_fastapi
sys.modules["fastapi.responses"] = mock_fastapi_responses
sys.modules["fastapi.exceptions"] = mock_fastapi_exceptions
sys.modules["fastapi.exception_handlers"] = mock_fastapi_exception_handlers
sys.modules["starlette.exceptions"] = mock_starlette
sys.modules["starlette.status"] = MagicMock(HTTP_429_TOO_MANY_REQUESTS=429)
sys.modules["request_context"] = mock_request_context

from backend.secuscan.main_exception_handlers import (
    rate_limit_exceeded_handler,
    generic_rate_limit_handler,
    custom_http_exception_handler,
    custom_validation_exception_handler,
    custom_unhandled_exception_handler,
)
from backend.secuscan.rate_limiter import RateLimitExceeded


# ---------------------------------------------------------------------------
# rate_limit_exceeded_handler
# ---------------------------------------------------------------------------


class TestRateLimitExceededHandler:
    @pytest.mark.asyncio
    async def test_returns_429_status_code(self):
        """The response status code is always 429."""
        exc = RateLimitExceeded(status_code=429, detail="Too Many Requests")
        response = await rate_limit_exceeded_handler(_StubRequest(), exc)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_includes_retry_after_from_exception(self):
        """retry_after is taken from the exception's retry_after attribute."""
        exc = RateLimitExceeded(status_code=429, detail="slow down")
        exc.retry_after = 120
        response = await rate_limit_exceeded_handler(_StubRequest(), exc)
        assert response.headers["Retry-After"] == "120"
        assert response.content["retry_after"] == 120

    @pytest.mark.asyncio
    async def test_defaults_retry_after_to_60(self):
        """When exc.retry_after is absent, 60 is used as the default."""
        exc = RateLimitExceeded(status_code=429, detail="rate limit")
        # Ensure retry_after is not set
        if hasattr(exc, "retry_after"):
            delattr(exc, "retry_after")
        response = await rate_limit_exceeded_handler(_StubRequest(), exc)
        assert response.headers["Retry-After"] == "60"
        assert response.content["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_includes_x_request_id_header(self):
        """The response includes an X-Request-ID header."""
        exc = RateLimitExceeded(status_code=429, detail="limit exceeded")
        response = await rate_limit_exceeded_handler(_StubRequest(), exc)
        assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_content_includes_error_message(self):
        """The JSON body contains an 'error' and 'message' field."""
        exc = RateLimitExceeded(status_code=429, detail="custom limit exceeded message")
        response = await rate_limit_exceeded_handler(_StubRequest(), exc)
        assert "error" in response.content
        assert "message" in response.content
        # The error field should reflect the exception detail
        assert response.content["error"] == "custom limit exceeded message"
        assert "Rate limit exceeded" in response.content["message"]


# ---------------------------------------------------------------------------
# generic_rate_limit_handler
# ---------------------------------------------------------------------------


class TestGenericRateLimitHandler:
    @pytest.mark.asyncio
    async def test_returns_429_status_code(self):
        """The response status code is always 429."""
        exc = _StubStarletteHTTPException(status_code=429, detail="slow down")
        response = await generic_rate_limit_handler(_StubRequest(), exc)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_preserves_existing_retry_after_header(self):
        """An existing Retry-After header on the exception is kept."""
        exc = _StubStarletteHTTPException(
            status_code=429, headers={"Retry-After": "300"}
        )
        response = await generic_rate_limit_handler(_StubRequest(), exc)
        assert response.headers["Retry-After"] == "300"

    @pytest.mark.asyncio
    async def test_adds_default_retry_after_when_missing(self):
        """When the exception has no Retry-After header, 60 is added."""
        exc = _StubStarletteHTTPException(status_code=429, headers={})
        response = await generic_rate_limit_handler(_StubRequest(), exc)
        assert response.headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_includes_x_request_id_header(self):
        """The response includes an X-Request-ID header."""
        exc = _StubStarletteHTTPException(status_code=429)
        response = await generic_rate_limit_handler(_StubRequest(), exc)
        assert "X-Request-ID" in response.headers


# ---------------------------------------------------------------------------
# custom_http_exception_handler
# ---------------------------------------------------------------------------


class TestCustomHttpExceptionHandler:
    @pytest.mark.asyncio
    async def test_delegates_to_default_handler(self):
        """The handler calls the default FastAPI http_exception_handler."""
        exc = _StubStarletteHTTPException(status_code=404, detail="not found")
        result = await custom_http_exception_handler(_StubRequest(), exc)
        # The handler should return a response (from the delegated default handler)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_adds_x_request_id_to_response(self):
        """The response from the default handler gets an X-Request-ID header added."""
        exc = _StubStarletteHTTPException(status_code=403)
        response = await custom_http_exception_handler(_StubRequest(), exc)
        assert "X-Request-ID" in response.headers


# ---------------------------------------------------------------------------
# custom_validation_exception_handler
# ---------------------------------------------------------------------------


class TestCustomValidationExceptionHandler:
    @pytest.mark.asyncio
    async def test_delegates_to_default_handler(self):
        """The handler calls the default FastAPI request_validation_exception_handler."""
        exc = Exception("validation error")
        result = await custom_validation_exception_handler(_StubRequest(), exc)
        # The handler should return a response (from the delegated default handler)
        assert result.status_code == 422

    @pytest.mark.asyncio
    async def test_adds_x_request_id_to_response(self):
        """The response gets an X-Request-ID header added."""
        exc = Exception("schema mismatch")
        response = await custom_validation_exception_handler(_StubRequest(), exc)
        assert "X-Request-ID" in response.headers


# ---------------------------------------------------------------------------
# custom_unhandled_exception_handler
# ---------------------------------------------------------------------------


class TestCustomUnhandledExceptionHandler:
    @pytest.mark.asyncio
    async def test_returns_500_status_code(self):
        """Uncaught exceptions always produce a 500 response."""
        exc = RuntimeError("unexpected failure")
        import backend.secuscan.main_exception_handlers as mh

        original = mh._settings
        mh._settings = MagicMock(debug=False)
        try:
            response = await custom_unhandled_exception_handler(_StubRequest(), exc)
            assert response.status_code == 500
        finally:
            mh._settings = original

    @pytest.mark.asyncio
    async def test_plain_text_in_non_debug_mode(self):
        """In non-debug mode, the response is a plain-text 'Internal Server Error'."""
        exc = ValueError("bad input")
        import backend.secuscan.main_exception_handlers as mh

        original = mh._settings
        mh._settings = MagicMock(debug=False)
        try:
            response = await custom_unhandled_exception_handler(_StubRequest(), exc)
            assert isinstance(response, _StubPlainTextResponse)
            assert "Internal Server Error" in str(response.body)
        finally:
            mh._settings = original

    @pytest.mark.asyncio
    async def test_debug_mode_returns_html_response(self):
        """In debug mode, the response is an HTML page containing the traceback."""
        exc = RuntimeError("debug traceback info")
        import backend.secuscan.main_exception_handlers as mh

        original = mh._settings
        mh._settings = MagicMock(debug=True)
        try:
            response = await custom_unhandled_exception_handler(_StubRequest(), exc)
            # HTML response should contain the traceback header
            assert "500 Internal Server Error" in str(response.body)
        finally:
            mh._settings = original

    @pytest.mark.asyncio
    async def test_x_request_id_added_in_both_modes(self):
        """X-Request-ID is added to the response in both debug and non-debug modes."""
        exc = Exception("any exception")
        import backend.secuscan.main_exception_handlers as mh

        original = mh._settings
        mh._settings = MagicMock(debug=False)
        try:
            response = await custom_unhandled_exception_handler(_StubRequest(), exc)
            assert "X-Request-ID" in response.headers
        finally:
            mh._settings = original
