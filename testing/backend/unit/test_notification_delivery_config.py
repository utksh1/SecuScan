"""
Unit tests for get_delivery_configuration in backend/secuscan/notification_service.py.

Verifies the notification delivery configuration structure returned by the
get_delivery_configuration helper function.
"""

from backend.secuscan.notification_service import get_delivery_configuration


class TestGetDeliveryConfiguration:
    def test_returns_expected_keys(self):
        """get_delivery_configuration returns a dict with all expected keys."""
        config = get_delivery_configuration()
        expected_keys = {
            "webhook_timeout_seconds",
            "webhook_connect_timeout_seconds",
            "max_retries",
            "backoff_factor_seconds",
        }
        assert set(config.keys()) == expected_keys

    def test_webhook_timeout_is_numeric(self):
        """webhook_timeout_seconds is a positive numeric value."""
        config = get_delivery_configuration()
        assert isinstance(config["webhook_timeout_seconds"], (int, float))
        assert config["webhook_timeout_seconds"] > 0

    def test_webhook_connect_timeout_is_numeric(self):
        """webhook_connect_timeout_seconds is a positive numeric value."""
        config = get_delivery_configuration()
        assert isinstance(config["webhook_connect_timeout_seconds"], (int, float))
        assert config["webhook_connect_timeout_seconds"] > 0

    def test_max_retries_is_zero(self):
        """max_retries is currently 0 (no automatic retries configured)."""
        config = get_delivery_configuration()
        assert config["max_retries"] == 0

    def test_backoff_factor_is_zero(self):
        """backoff_factor_seconds is currently 0 (no exponential backoff)."""
        config = get_delivery_configuration()
        assert config["backoff_factor_seconds"] == 0.0

    def test_timeout_greater_than_connect_timeout(self):
        """Total timeout exceeds connect timeout (connect is a subset of total)."""
        config = get_delivery_configuration()
        assert config["webhook_timeout_seconds"] > config["webhook_connect_timeout_seconds"]

    def test_dict_has_exactly_four_keys(self):
        """The configuration dict contains exactly 4 keys."""
        config = get_delivery_configuration()
        assert len(config) == 4
