"""
Unit tests for notification validation helpers in backend.secuscan.routes_email_validation.

Tests the email format regex and validation logic extracted from routes.py.
"""

from backend.secuscan.routes_email_validation import (
    validate_email_format,
    strip_target,
    validate_notification_target,
    NotificationValidationError,
)


class TestValidateEmailFormat:
    def test_valid_email(self):
        is_valid, error = validate_email_format("user@example.com")
        assert is_valid is True
        assert error == ""

    def test_valid_email_uppercase_domain(self):
        is_valid, error = validate_email_format("user@EXAMPLE.COM")
        assert is_valid is True

    def test_valid_email_subdomain(self):
        is_valid, error = validate_email_format("user@mail.example.com")
        assert is_valid is True

    def test_valid_email_plus_sign(self):
        is_valid, error = validate_email_format("user+tag@example.com")
        assert is_valid is True

    def test_missing_tld_raises(self):
        is_valid, error = validate_email_format("user@hostname")
        assert is_valid is False
        assert "Invalid email address" in error

    def test_missing_at_symbol(self):
        is_valid, error = validate_email_format("notanemail")
        assert is_valid is False

    def test_spaces_in_email_raises(self):
        is_valid, error = validate_email_format("bad email@test.com")
        assert is_valid is False

    def test_empty_string_raises(self):
        is_valid, error = validate_email_format("")
        assert is_valid is False
        assert "Email address is required" in error

    def test_whitespace_only_raises(self):
        is_valid, error = validate_email_format("   ")
        assert is_valid is False
        assert "Email address is required" in error

    def test_none_raises(self):
        is_valid, error = validate_email_format(None)
        assert is_valid is False


class TestStripTarget:
    def test_strips_leading_whitespace(self):
        assert strip_target("  hello") == "hello"

    def test_strips_trailing_whitespace(self):
        assert strip_target("hello  ") == "hello"

    def test_strips_both(self):
        assert strip_target("  hello world  ") == "hello world"

    def test_no_change_for_clean_string(self):
        assert strip_target("clean@email.com") == "clean@email.com"


class TestValidateNotificationTarget:
    def test_webhook_valid_https_url(self):
        result = validate_notification_target("webhook", "https://example.com/hook")
        assert result == "https://example.com/hook"

    def test_webhook_valid_http_url(self):
        result = validate_notification_target("webhook", "http://localhost:9000/webhook")
        assert result == "http://localhost:9000/webhook"

    def test_webhook_invalid_url_no_scheme_raises(self):
        with __import__("pytest").raises(NotificationValidationError) as ctx:
            validate_notification_target("webhook", "not-a-url")
        assert "Invalid webhook URL" in str(ctx.value)

    def test_webhook_empty_target_raises(self):
        with __import__("pytest").raises(NotificationValidationError) as ctx:
            validate_notification_target("webhook", "")
        assert "Notification target is required" in str(ctx.value)

    def test_webhook_whitespace_target_raises(self):
        with __import__("pytest").raises(NotificationValidationError):
            validate_notification_target("webhook", "   ")

    def test_email_valid_address(self):
        result = validate_notification_target("email", "test@example.com")
        assert result == "test@example.com"

    def test_email_valid_address_uppercase_domain(self):
        result = validate_notification_target("email", "user@EXAMPLE.COM")
        assert result == "user@EXAMPLE.COM"

    def test_email_missing_tld_raises(self):
        with __import__("pytest").raises(NotificationValidationError) as ctx:
            validate_notification_target("email", "user@hostname")
        assert "Invalid email address" in str(ctx.value)

    def test_email_spaces_in_address_raises(self):
        with __import__("pytest").raises(NotificationValidationError) as ctx:
            validate_notification_target("email", "bad email@test.com")
        assert "Invalid email address" in str(ctx.value)

    def test_email_empty_target_raises(self):
        with __import__("pytest").raises(NotificationValidationError) as ctx:
            validate_notification_target("email", "")
        assert "Notification target is required" in str(ctx.value)

    def test_whitespace_stripped_from_valid_email(self):
        result = validate_notification_target("email", "  user@test.com  ")
        assert result == "user@test.com"

    def test_whitespace_stripped_from_valid_webhook(self):
        result = validate_notification_target("webhook", "  https://example.com  ")
        assert result == "https://example.com"

    def test_unknown_channel_type_raises(self):
        with __import__("pytest").raises(NotificationValidationError) as ctx:
            validate_notification_target("sms", "+1234567890")
        assert "Unknown channel type" in str(ctx.value)
