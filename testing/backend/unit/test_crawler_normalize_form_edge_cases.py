"""
Unit tests for crawler _normalize_form edge cases.

Tests CSRF token detection, state-changing form detection via input types,
password field counting, URL normalization for form action, and input_count.
Existing tests in test_crawler_surface_parsing.py cover DELETE method and
non-dict input item tolerance; this file covers the remaining edge cases.
"""

from __future__ import annotations

import pytest

from backend.secuscan.crawler import _normalize_form


# ---------------------------------------------------------------------------
# CSRF token detection
# ---------------------------------------------------------------------------

class TestNormalizeFormCsrfToken:
    @pytest.mark.parametrize(
        "token_name",
        [
            "csrf",
            "_csrf",
            "csrfmiddlewaretoken",
            "authenticity_token",
            "__requestverificationtoken",
        ],
    )
    def test_has_csrf_token_true_for_known_csrf_names(self, token_name):
        """Each known CSRF token name should set has_csrf_token=True."""
        form = {
            "method": "post",
            "action": "/submit",
            "inputs": [{"name": token_name, "type": "hidden"}],
        }
        result = _normalize_form("https://example.com/page", form)
        assert result["has_csrf_token"] is True

    def test_has_csrf_token_false_for_regular_input_names(self):
        """Normal input names should not trigger has_csrf_token."""
        form = {
            "method": "post",
            "action": "/login",
            "inputs": [{"name": "username", "type": "text"}, {"name": "password", "type": "password"}],
        }
        result = _normalize_form("https://example.com/login", form)
        assert result["has_csrf_token"] is False

    def test_has_csrf_token_false_for_unknown_csrf_like_name(self):
        """Names that contain 'csrf' as substring but are not exact matches should not trigger."""
        form = {
            "method": "post",
            "action": "/submit",
            "inputs": [{"name": "csrf_form_token", "type": "hidden"}],
        }
        result = _normalize_form("https://example.com/page", form)
        assert result["has_csrf_token"] is False

    def test_has_csrf_token_false_when_no_inputs(self):
        """Empty inputs list should result in has_csrf_token=False."""
        form = {"method": "get", "action": "/search", "inputs": []}
        result = _normalize_form("https://example.com", form)
        assert result["has_csrf_token"] is False


# ---------------------------------------------------------------------------
# State-changing detection via input types
# ---------------------------------------------------------------------------

class TestNormalizeFormStateChanging:
    def test_state_changing_true_for_password_input_type(self):
        """A GET form with a password field should be marked state_changing=True."""
        form = {
            "method": "get",
            "action": "/search",
            "inputs": [{"name": "username", "type": "text"}, {"name": "password", "type": "password"}],
        }
        result = _normalize_form("https://example.com/login", form)
        assert result["state_changing"] is True

    def test_state_changing_true_for_file_input_type(self):
        """A GET form with a file field should be marked state_changing=True."""
        form = {
            "method": "get",
            "action": "/upload",
            "inputs": [{"name": "avatar", "type": "file"}],
        }
        result = _normalize_form("https://example.com/upload", form)
        assert result["state_changing"] is True

    def test_state_changing_true_for_hidden_input_type(self):
        """A GET form with a hidden field should be marked state_changing=True."""
        form = {
            "method": "get",
            "action": "/search",
            "inputs": [{"name": "page", "type": "hidden", "value": "2"}],
        }
        result = _normalize_form("https://example.com", form)
        assert result["state_changing"] is True

    def test_state_changing_true_for_post_without_special_inputs(self):
        """POST method without special inputs should still be state_changing=True."""
        form = {
            "method": "post",
            "action": "/comment",
            "inputs": [{"name": "text", "type": "textarea"}],
        }
        result = _normalize_form("https://example.com/post", form)
        assert result["state_changing"] is True

    def test_state_changing_false_for_get_with_text_only(self):
        """A GET form with only text inputs should not be state_changing."""
        form = {
            "method": "get",
            "action": "/search",
            "inputs": [{"name": "q", "type": "text"}],
        }
        result = _normalize_form("https://example.com/search", form)
        assert result["state_changing"] is False


# ---------------------------------------------------------------------------
# Password field counting
# ---------------------------------------------------------------------------

class TestNormalizeFormPasswordFields:
    def test_password_fields_count_matches_password_inputs(self):
        """password_fields should equal the number of type=password inputs."""
        form = {
            "method": "post",
            "action": "/login",
            "inputs": [
                {"name": "username", "type": "text"},
                {"name": "password", "type": "password"},
                {"name": "confirm_password", "type": "password"},
            ],
        }
        result = _normalize_form("https://example.com/login", form)
        assert result["password_fields"] == 2

    def test_password_fields_zero_for_no_password_inputs(self):
        """Forms without password inputs should have password_fields=0."""
        form = {
            "method": "get",
            "action": "/search",
            "inputs": [{"name": "q", "type": "text"}],
        }
        result = _normalize_form("https://example.com/search", form)
        assert result["password_fields"] == 0

    def test_password_fields_ignores_non_dict_inputs(self):
        """Non-dict items in inputs should not contribute to password_fields count."""
        form = {
            "method": "post",
            "action": "/submit",
            "inputs": ["not-a-dict", {"name": "pass", "type": "password"}],
        }
        result = _normalize_form("https://example.com/submit", form)
        assert result["password_fields"] == 1


# ---------------------------------------------------------------------------
# Input count
# ---------------------------------------------------------------------------

class TestNormalizeFormInputCount:
    def test_input_count_reflects_all_inputs(self):
        """input_count should equal the total number of input items."""
        form = {
            "method": "post",
            "action": "/submit",
            "inputs": [{"name": "a", "type": "text"}, {"name": "b", "type": "hidden"}],
        }
        result = _normalize_form("https://example.com/submit", form)
        assert result["input_count"] == 2

    def test_input_count_zero_for_empty_inputs(self):
        """Empty inputs list should result in input_count=0."""
        form = {"method": "get", "action": "/search", "inputs": []}
        result = _normalize_form("https://example.com/search", form)
        assert result["input_count"] == 0

    def test_input_count_with_non_list_inputs(self):
        """Non-list inputs value should result in input_count=0 (not crash)."""
        form = {"method": "get", "action": "/search", "inputs": "not-a-list"}
        result = _normalize_form("https://example.com/search", form)
        assert result["input_count"] == 0


# ---------------------------------------------------------------------------
# Action URL normalization
# ---------------------------------------------------------------------------

class TestNormalizeFormActionUrl:
    def test_action_urljoin_resolves_relative_action(self):
        """Relative action URL should be resolved against the page URL."""
        result = _normalize_form("https://example.com/page", {"method": "get", "action": "/submit"})
        assert result["action"] == "https://example.com/submit"

    def test_action_urljoin_handles_absolute_action(self):
        """Absolute URL in action should be returned unchanged."""
        form = {
            "method": "post",
            "action": "https://other.com/process",
            "inputs": [],
        }
        result = _normalize_form("https://example.com/page", form)
        assert result["action"] == "https://other.com/process"

    def test_action_empty_string_uses_page_url(self):
        """Empty action should resolve to the page URL itself."""
        form = {"method": "post", "action": "", "inputs": []}
        result = _normalize_form("https://example.com/page", form)
        assert result["action"] == "https://example.com/page"

    def test_action_none_defaults_to_page_url(self):
        """Missing action should default to the page URL."""
        form = {"method": "post", "inputs": []}
        result = _normalize_form("https://example.com/page", form)
        assert result["action"] == "https://example.com/page"


# ---------------------------------------------------------------------------
# Output shape and field preservation
# ---------------------------------------------------------------------------

class TestNormalizeFormOutputShape:
    def test_preserves_original_form_fields(self):
        """Original form keys should be preserved in the output dict."""
        form = {
            "method": "post",
            "action": "/submit",
            "inputs": [],
            "enctype": "multipart/form-data",
            "id": "login-form",
        }
        result = _normalize_form("https://example.com", form)
        assert result["enctype"] == "multipart/form-data"
        assert result["id"] == "login-form"

    def test_page_url_is_set_correctly(self):
        """page_url should always be set to the passed-in page URL."""
        form = {"method": "get", "action": "/", "inputs": []}
        result = _normalize_form("https://example.com/login", form)
        assert result["page_url"] == "https://example.com/login"
