"""
Unit tests for notification service webhook timeout handling.

Verifies that webhook timeouts are caught and recorded as failures rather than
propagating and crashing the notification delivery loop.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


class _MockAsyncClient:
    """Minimal async context manager that raises configured errors on post()."""

    def __init__(self, error_to_raise: Exception | None = None):
        self._error = error_to_raise
        self._closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self._closed = True

    async def post(self, *args, **kwargs):
        if self._error:
            raise self._error
        return MagicMock(
            status_code=200,
            headers={},
        )


class TestSendWebhookTimeout:
    """Tests for send_webhook timeout behavior."""

    @pytest.mark.asyncio
    async def test_connect_timeout_returns_failure_tuple(self):
        """Connect timeout is caught and returns (False, error_message)."""
        from backend.secuscan.notification_service import send_webhook

        with patch("backend.secuscan.notification_service.httpx.AsyncClient") as MockClient:
            MockClient.return_value = _MockAsyncClient(
                error_to_raise=httpx.ConnectTimeout("Connection timed out")
            )
            ok, error = await send_webhook(
                "https://example.com/webhook",
                {"finding": "test"},
            )

        assert ok is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_read_timeout_returns_failure_tuple(self):
        """Read timeout is caught and returns (False, error_message)."""
        from backend.secuscan.notification_service import send_webhook

        with patch("backend.secuscan.notification_service.httpx.AsyncClient") as MockClient:
            MockClient.return_value = _MockAsyncClient(
                error_to_raise=httpx.ReadTimeout("Read timed out after 10s")
            )
            ok, error = await send_webhook(
                "https://example.com/webhook",
                {"finding": "test"},
            )

        assert ok is False
        assert "timed out" in error.lower() or "timeout" in error.lower()

    @pytest.mark.asyncio
    async def test_timeout_exception_does_not_propagate(self):
        """Timeout exceptions should not propagate from send_webhook."""
        from backend.secuscan.notification_service import send_webhook

        with patch("backend.secuscan.notification_service.httpx.AsyncClient") as MockClient:
            MockClient.return_value = _MockAsyncClient(
                error_to_raise=httpx.TimeoutException("General timeout")
            )
            # Should NOT raise — timeout is caught
            ok, error = await send_webhook(
                "https://example.com/webhook",
                {"finding": "test"},
            )
            assert ok is False

    @pytest.mark.asyncio
    async def test_connect_error_returns_failure_tuple(self):
        """Connection error also returns failure tuple."""
        from backend.secuscan.notification_service import send_webhook

        with patch("backend.secuscan.notification_service.httpx.AsyncClient") as MockClient:
            MockClient.return_value = _MockAsyncClient(
                error_to_raise=httpx.ConnectError("Connection refused")
            )
            ok, error = await send_webhook(
                "https://example.com/webhook",
                {"finding": "test"},
            )

        assert ok is False
        assert error is not None


class TestGetDeliveryConfiguration:
    """Tests for delivery configuration including timeout values."""

    def test_get_delivery_configuration_returns_timeout(self):
        """get_delivery_configuration returns the configured timeout."""
        from backend.secuscan.notification_service import get_delivery_configuration

        config = get_delivery_configuration()

        assert "webhook_timeout_seconds" in config
        assert config["webhook_timeout_seconds"] == 10.0
        assert "webhook_connect_timeout_seconds" in config
        assert config["webhook_connect_timeout_seconds"] == 5.0
        assert "max_retries" in config
        assert "backoff_factor_seconds" in config
