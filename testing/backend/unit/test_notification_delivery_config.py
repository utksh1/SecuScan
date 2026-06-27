"""
Unit tests for backend.secuscan.notification_service.get_delivery_configuration.

Covers:
- Returns the expected dict structure with all required keys
- webhook_timeout_seconds has the expected value
- webhook_connect_timeout_seconds has the expected value
- max_retries is 0
- backoff_factor_seconds is 0.0
"""

from __future__ import annotations

from backend.secuscan.notification_service import get_delivery_configuration


class TestGetDeliveryConfiguration:
    def test_returns_dict(self):
        """get_delivery_configuration returns a dict."""
        result = get_delivery_configuration()
        assert isinstance(result, dict)

    def test_has_webhook_timeout_seconds(self):
        """Returned dict contains webhook_timeout_seconds key."""
        result = get_delivery_configuration()
        assert "webhook_timeout_seconds" in result
        assert isinstance(result["webhook_timeout_seconds"], (int, float))

    def test_has_webhook_connect_timeout_seconds(self):
        """Returned dict contains webhook_connect_timeout_seconds key."""
        result = get_delivery_configuration()
        assert "webhook_connect_timeout_seconds" in result
        assert isinstance(result["webhook_connect_timeout_seconds"], (int, float))

    def test_max_retries_is_zero(self):
        """max_retries is currently 0 (no automatic retry)."""
        result = get_delivery_configuration()
        assert result["max_retries"] == 0

    def test_backoff_factor_is_zero(self):
        """backoff_factor_seconds is currently 0.0 (no backoff)."""
        result = get_delivery_configuration()
        assert result["backoff_factor_seconds"] == 0.0

    def test_webhook_timeout_greater_than_connect_timeout(self):
        """Total timeout is greater than connect timeout."""
        result = get_delivery_configuration()
        assert result["webhook_timeout_seconds"] > result["webhook_connect_timeout_seconds"]

    def test_result_is_deterministic(self):
        """Calling the function twice returns the same result."""
        r1 = get_delivery_configuration()
        r2 = get_delivery_configuration()
        assert r1 == r2

    def test_all_expected_keys_present(self):
        """All expected keys are present in the result."""
        expected_keys = {
            "webhook_timeout_seconds",
            "webhook_connect_timeout_seconds",
            "max_retries",
            "backoff_factor_seconds",
        }
        result = get_delivery_configuration()
        assert set(result.keys()) == expected_keys
