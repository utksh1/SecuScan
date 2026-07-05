"""
Unit tests for email validation helpers in backend.secuscan.routes_email_validation.

Tests the email format regex and validation logic extracted from routes.py.
"""

from backend.secuscan.routes_email_validation import (
    validate_email_format,
    strip_target,
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
        assert "Invalid email address" in error

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
