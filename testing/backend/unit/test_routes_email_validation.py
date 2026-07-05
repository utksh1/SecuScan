"""
Unit tests for validate_notification_target in backend.secuscan.routes_email_validation.

Tests the notification-target validation path for both webhook and email channels.
"""

import pytest
from backend.secuscan.routes_email_validation import (
    validate_notification_target,
    validate_email_format,
    WEBHOOK_TYPE,
    EMAIL_TYPE,
)


# ---------------------------------------------------------------------------
# validate_email_format
# ---------------------------------------------------------------------------

class TestValidateEmailFormat:
    def test_valid_address_stripped(self):
        result = validate_email_format("  Test@Example.COM  ")
        assert result == "Test@Example.COM"

    def test_valid_simple_address(self):
        assert validate_email_format("alice@example.org") == "alice@example.org"

    def test_missing_at_symbol_raises(self):
        with pytest.raises(ValueError, match="Invalid email address"):
            validate_email_format("notanemail")

    def test_missing_domain_raises(self):
        with pytest.raises(ValueError, match="Invalid email address"):
            validate_email_format("user@")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Email address is required"):
            validate_email_format("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="Email address is required"):
            validate_email_format("   ")

    def test_leading_trailing_spaces_stripped(self):
        assert validate_email_format("  bob@example.com  ") == "bob@example.com"


# ---------------------------------------------------------------------------
# validate_notification_target (webhook channel)
# ---------------------------------------------------------------------------

class TestValidateNotificationTargetWebhook:
    def test_valid_http_url(self, monkeypatch):
        monkeypatch.setattr(
            "backend.secuscan.routes_email_validation.validate_webhook_url",
            lambda url: (True, None),
        )
        result = validate_notification_target(WEBHOOK_TYPE, "http://example.com/hook")
        assert result == "http://example.com/hook"

    def test_valid_https_url(self, monkeypatch):
        monkeypatch.setattr(
            "backend.secuscan.routes_email_validation.validate_webhook_url",
            lambda url: (True, None),
        )
        result = validate_notification_target(WEBHOOK_TYPE, "  https://discord.com/api/webhooks/1/abc  ")
        assert result == "https://discord.com/api/webhooks/1/abc"

    def test_invalid_url_raises(self, monkeypatch):
        monkeypatch.setattr(
            "backend.secuscan.routes_email_validation.validate_webhook_url",
            lambda url: (False, "URL must start with http or https"),
        )
        with pytest.raises(ValueError, match="URL must start with http or https"):
            validate_notification_target(WEBHOOK_TYPE, "ftp://evil.com")

    def test_empty_target_raises(self, monkeypatch):
        with pytest.raises(ValueError, match="Notification target is required"):
            validate_notification_target(WEBHOOK_TYPE, "")

    def test_whitespace_target_raises(self, monkeypatch):
        with pytest.raises(ValueError, match="Notification target is required"):
            validate_notification_target(WEBHOOK_TYPE, "   ")

    def test_ssrf_blocked_raises(self, monkeypatch):
        monkeypatch.setattr(
            "backend.secuscan.routes_email_validation.validate_webhook_url",
            lambda url: (True, None),
        )
        monkeypatch.setattr(
            "backend.secuscan.validation.resolve_and_validate_target",
            lambda url: (False, "Resolved to private IP 10.0.0.1"),
        )
        monkeypatch.setattr(
            "backend.secuscan.validation.validate_webhook_target",
            lambda url: (True, None),
        )
        with pytest.raises(ValueError, match="SSRF protection"):
            validate_notification_target(WEBHOOK_TYPE, "https://evil.com/hook")

    def test_ssrf_passes_when_disabled(self, monkeypatch):
        monkeypatch.setattr(
            "backend.secuscan.routes_email_validation.validate_webhook_url",
            lambda url: (True, None),
        )
        # Even if SSRF would block, it should be skipped
        monkeypatch.setattr(
            "backend.secuscan.validation.resolve_and_validate_target",
            lambda url: (False, "Blocked"),
        )
        result = validate_notification_target(
            WEBHOOK_TYPE, "https://public.example.com/hook",
            notification_ssrf_enabled=False,
        )
        assert result == "https://public.example.com/hook"


# ---------------------------------------------------------------------------
# validate_notification_target (email channel)
# ---------------------------------------------------------------------------

class TestValidateNotificationTargetEmail:
    def test_valid_email(self):
        result = validate_notification_target(EMAIL_TYPE, "alice@example.org")
        assert result == "alice@example.org"

    def test_email_stripped(self):
        result = validate_notification_target(EMAIL_TYPE, "  bob@example.org  ")
        assert result == "bob@example.org"

    def test_invalid_email_raises(self):
        with pytest.raises(ValueError, match="Invalid email address"):
            validate_notification_target(EMAIL_TYPE, "not-an-email")

    def test_empty_email_raises(self):
        with pytest.raises(ValueError, match="Notification target is required"):
            validate_notification_target(EMAIL_TYPE, "")

    def test_whitespace_email_raises(self):
        with pytest.raises(ValueError, match="Notification target is required"):
            validate_notification_target(EMAIL_TYPE, "  ")
