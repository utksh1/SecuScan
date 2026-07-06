"""
Unit tests for get_delivery_configuration in notification_service.

Tests that the function returns the correct static configuration dict
for webhook/email delivery parameters.
"""

from __future__ import annotations

import pytest

from backend.secuscan.notification_service import get_delivery_configuration


class TestGetDeliveryConfiguration:
    def test_returns_expected_keys(self):
        """All required keys must be present in the returned dict."""
        cfg = get_delivery_configuration()
        assert "webhook_timeout_seconds" in cfg
        assert "webhook_connect_timeout_seconds" in cfg
        assert "max_retries" in cfg
        assert "backoff_factor_seconds" in cfg

    def test_webhook_timeout_is_positive_number(self):
        """webhook_timeout_seconds must be a positive number (int or float)."""
        cfg = get_delivery_configuration()
        assert isinstance(cfg["webhook_timeout_seconds"], (int, float))
        assert cfg["webhook_timeout_seconds"] > 0

    def test_webhook_connect_timeout_is_positive_number(self):
        """webhook_connect_timeout_seconds must be a positive number (int or float)."""
        cfg = get_delivery_configuration()
        assert isinstance(cfg["webhook_connect_timeout_seconds"], (int, float))
        assert cfg["webhook_connect_timeout_seconds"] > 0

    def test_max_retries_is_zero(self):
        """max_retries is currently 0 (no retries configured)."""
        cfg = get_delivery_configuration()
        assert cfg["max_retries"] == 0

    def test_backoff_factor_is_zero(self):
        """backoff_factor_seconds is currently 0.0."""
        cfg = get_delivery_configuration()
        assert cfg["backoff_factor_seconds"] == 0.0

    def test_returns_new_dict_each_call(self):
        """Each call returns an independent dict — no shared mutable state."""
        cfg1 = get_delivery_configuration()
        cfg2 = get_delivery_configuration()
        assert cfg1 is not cfg2
        cfg1["webhook_timeout_seconds"] = 999
        assert cfg2["webhook_timeout_seconds"] != 999

    def test_timeout_values_are_reasonable(self):
        """Timeout values should be within reasonable bounds (<300s)."""
        cfg = get_delivery_configuration()
        assert cfg["webhook_timeout_seconds"] < 300
        assert cfg["webhook_connect_timeout_seconds"] < 300
