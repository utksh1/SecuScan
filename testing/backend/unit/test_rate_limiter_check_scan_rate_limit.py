"""
Unit tests for check_scan_rate_limit async dependency in rate_limiter.py.

The rate_limiter module imports redis.asyncio and fastapi. We mock these at the
sys.modules level so the test can import and run the function without those
dependencies being installed.
"""
import sys
from unittest.mock import MagicMock, AsyncMock
import pytest


# ---------------------------------------------------------------------------
# Mock heavy dependencies BEFORE importing the module under test
# ---------------------------------------------------------------------------

class _StubHTTPException(Exception):
    def __init__(self, status_code: int, detail=None, headers=None):
        self.status_code = status_code
        self.detail = detail or {}
        self.headers = headers or {}
        super().__init__(str(detail))


class _StubStatus:
    HTTP_429_TOO_MANY_REQUESTS = 429


mock_fastapi = MagicMock()
mock_fastapi.HTTPException = _StubHTTPException
mock_fastapi.status = _StubStatus()

sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()
sys.modules["fastapi"] = mock_fastapi


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

from backend.secuscan.rate_limiter import check_scan_rate_limit


class StubState:
    """Minimal object that provides request.app.state.scan_rate_limiter."""
    def __init__(self, limiter=None):
        self.scan_rate_limiter = limiter


class StubApp:
    """Minimal object that provides request.app.state."""
    def __init__(self, limiter=None):
        self.state = StubState(limiter)


class StubRequest:
    """Minimal request object with headers and app.state."""
    def __init__(self, headers=None, limiter=None):
        self.headers = headers or {}
        self.app = StubApp(limiter)


class TestCheckScanRateLimit:
    """Test the check_scan_rate_limit FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_calls_limiter_check_when_limiter_is_set(self):
        """When scan_rate_limiter is present in app.state, call limiter.check()."""
        mock_limiter = AsyncMock()
        mock_request = StubRequest(limiter=mock_limiter)

        await check_scan_rate_limit(mock_request)

        mock_limiter.check.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_raises_when_limiter_check_raises_httpexception(self):
        """When limiter.check() raises HTTPException, it should propagate."""
        from fastapi import HTTPException
        mock_limiter = AsyncMock()
        mock_limiter.check.side_effect = HTTPException(status_code=429, detail="rate limit")
        mock_request = StubRequest(limiter=mock_limiter)

        with pytest.raises(HTTPException) as exc_info:
            await check_scan_rate_limit(mock_request)

        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_noop_when_limiter_is_none(self):
        """When app.state.scan_rate_limiter is None, no-op without error."""
        mock_request = StubRequest(limiter=None)

        # Should not raise
        await check_scan_rate_limit(mock_request)

    @pytest.mark.asyncio
    async def test_noop_when_state_is_absent(self):
        """When request.app.state does not exist, no-op without AttributeError."""
        mock_request = MagicMock()
        # Make getattr(request.app.state, "scan_rate_limiter", None) return None
        mock_request.app.configure_mock(state=MagicMock(spec=[]))
        # Delete the scan_rate_limiter attribute so getattr returns None
        del mock_request.app.state.scan_rate_limiter

        # getattr with default None should return None
        limiter = getattr(mock_request.app.state, "scan_rate_limiter", None)
        assert limiter is None

        # Should not raise
        await check_scan_rate_limit(mock_request)
