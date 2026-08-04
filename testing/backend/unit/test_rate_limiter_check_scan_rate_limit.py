"""
Unit tests for check_scan_rate_limit async dependency in rate_limiter.py.

fastapi and redis.asyncio are available in the test environment, so the module
can be imported and tested directly without sys.modules mocking.
"""
from unittest.mock import MagicMock, AsyncMock
import pytest

from backend.secuscan.rate_limiter import check_scan_rate_limit
from fastapi import HTTPException


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
        """When request.app.state does not expose scan_rate_limiter, no-op."""
        mock_request = MagicMock()
        mock_request.app.configure_mock(state=MagicMock(spec=[]))
        # Delete scan_rate_limiter so getattr falls back to None
        del mock_request.app.state.scan_rate_limiter

        limiter = getattr(mock_request.app.state, "scan_rate_limiter", None)
        assert limiter is None

        # Should not raise
        await check_scan_rate_limit(mock_request)
