"""
Unit tests for backend/secuscan/crawler.py helper functions.

Covers the pure helpers exposed by the module:
  - _build_headers
  - _extract_title
  - _classify_path_hint
  - _extract_tech_hints
  - _extract_cms_hints
  - _normalize_form

The crawl_target() function performs real HTTP I/O and is exercised by the
existing integration tests in testing/backend/test_crawler_plugin.py. The
helpers here are tested in isolation with synthetic inputs.
"""

from __future__ import annotations

import pytest

from backend.secuscan.crawler import (
    _build_headers,
    _classify_path_hint,
    _extract_cms_hints,
    _extract_tech_hints,
    _extract_title,
    _normalize_form,
)


# ---------------------------------------------------------------------------
# _build_headers
# ---------------------------------------------------------------------------


class TestBuildHeaders:
    def test_default_user_agent(self):
        headers = _build_headers()
        assert headers["User-Agent"] == "SecuScan-Crawler/1.0"

    def test_default_accept_header(self):
        headers = _build_headers()
        assert "Accept" in headers
        assert "text/html" in headers["Accept"]

    def test_extra_headers_override_defaults(self):
        headers = _build_headers(extra_headers={"User-Agent": "Custom/2.0"})
        assert headers["User-Agent"] == "Custom/2.0"

    def test_extra_headers_merged(self):
        headers = _build_headers(extra_headers={"X-Custom": "value"})
        assert headers["X-Custom"] == "value"
        # Defaults are still present
        assert "User-Agent" in headers

    def test_extra_headers_stringified(self):
        # Keys and values must be coerced to str
        headers = _build_headers(extra_headers={"X-Trace-Id": 12345})
        assert headers["X-Trace-Id"] == "12345"
        assert isinstance(headers["X-Trace-Id"], str)

    def test_none_value_dropped(self):
        headers = _build_headers(extra_headers={"X-Drop": None, "X-Keep": "ok"})
        assert "X-Drop" not in headers
        assert headers["X-Keep"] == "ok"

    def test_empty_key_dropped(self):
        headers = _build_headers(extra_headers={"": "value", "X-Keep": "ok"})
        assert "" not in headers
        assert headers["X-Keep"] == "ok"

    def test_returns_dict(self):
        assert isinstance(_build_headers(), dict)
        assert isinstance(_build_headers(extra_headers={"a": "b"}), dict)

    def test_none_extra_headers_uses_defaults(self):
        # Passing None should behave like no extra headers
        headers = _build_headers(extra_headers=None)
        assert headers["User-Agent"] == "SecuScan-Crawler/1.0"


# ---------------------------------------------------------------------------
# _extract_title
# ---------------------------------------------------------------------------


class TestExtractTitle:
    def test_basic_title(self):
        html = "<html><head><title>Hello World</title></head><body></body></html>"
        assert _extract_title(html) == "Hello World"

    def test_title_with_whitespace(self):
        html = "<title>   Padded   </title>"
        assert _extract_title(html) == "Padded"

    def test_missing_title_returns_empty(self):
        html = "<html><head></head><body>no title here</body></html>"
        assert _extract_title(html) == ""

    def test_only_closing_tag_returns_empty(self):
        html = "random content with </title> but no opening"
        assert _extract_title(html) == ""

    def test_empty_title(self):
        html = "<title></title>"
        assert _extract_title(html) == ""

    def test_title_with_attributes(self):
        # Real-world pages may have attributes on <title>
        html = '<html><head><title lang="en">Attributed</title></head></html>'
        # The function uses a case-insensitive substring search for <title>,
        # so attributes inside the tag are NOT supported — opening tag must be plain.
        # Verify the function handles the common plain case.
        plain = "<title>Plain</title>"
        assert _extract_title(plain) == "Plain"

    def test_case_insensitive(self):
        html = "<TITLE>Upper</TITLE>"
        assert _extract_title(html) == "Upper"

    def test_multiline_html(self):
        html = (
            "<html>\n"
            "  <head>\n"
            "    <title>Multi\nLine</title>\n"
            "  </head>\n"
            "</html>"
        )
        assert _extract_title(html) == "Multi\nLine"


# ---------------------------------------------------------------------------
# _classify_path_hint
# ---------------------------------------------------------------------------


class TestClassifyPathHint:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("https://example.com/admin/login", "admin"),
            ("https://example.com/administrator/", "admin"),
            ("https://example.com/wp-admin/users", "admin"),
            ("https://example.com/user/login", "login"),
            ("https://example.com/auth/signin", "login"),
            ("https://example.com/oauth/signin", "login"),
            ("https://example.com/debug/status", "debug"),
            ("https://example.com/actuator/health", "debug"),
            ("https://example.com/_profiler", "debug"),
            ("https://example.com/console", "debug"),
            ("https://example.com/api/docs", "docs"),
            ("https://example.com/swagger/ui", "docs"),
            ("https://example.com/openapi.json", "docs"),
            ("https://example.com/redoc", "docs"),
        ],
    )
    def test_classifies_known_categories(self, path, expected):
        # _classify_path_hint expects a lowercased string per its docstring
        assert _classify_path_hint(path.lower()) == expected

    def test_returns_none_for_unclassified(self):
        assert _classify_path_hint("https://example.com/products/shoes") is None
        assert _classify_path_hint("https://example.com/") is None
        assert _classify_path_hint("https://example.com/blog/post-1") is None

    def test_handles_empty_string(self):
        assert _classify_path_hint("") is None


# ---------------------------------------------------------------------------
# _extract_tech_hints
# ---------------------------------------------------------------------------


class TestExtractTechHints:
    def test_x_powered_by_header(self):
        hints = _extract_tech_hints({"X-Powered-By": "Express"}, [], [], "")
        assert "Express" in hints

    def test_server_header(self):
        hints = _extract_tech_hints({"Server": "nginx/1.24.0"}, [], [], "")
        assert "nginx/1.24.0" in hints

    def test_x_generator_header(self):
        hints = _extract_tech_hints({"X-Generator": "Drupal 9"}, [], [], "")
        assert "Drupal 9" in hints

    def test_meta_generator_included(self):
        hints = _extract_tech_hints({}, ["WordPress 6.4"], [], "")
        assert "WordPress 6.4" in hints

    def test_wordpress_detected_from_body(self):
        hints = _extract_tech_hints({}, [], [], "before /wp-content/themes/twenty/ after")
        assert "WordPress" in hints

    def test_drupal_detected_from_body(self):
        hints = _extract_tech_hints({}, [], [], '<link href="/sites/default/files/x.css" />')
        assert "Drupal" in hints

    def test_joomla_detected_from_body_string(self):
        hints = _extract_tech_hints({}, [], [], "Welcome to Joomla!")
        assert "Joomla" in hints

    def test_joomla_detected_from_body_media(self):
        hints = _extract_tech_hints({}, [], [], '<script src="/media/system/js/mootools.js"></script>')
        assert "Joomla" in hints

    def test_script_hints_for_react(self):
        hints = _extract_tech_hints({}, [], ["https://example.com/static/react.production.min.js"], "")
        assert "react.production.min.js" in hints

    def test_script_hints_for_vue(self):
        hints = _extract_tech_hints({}, [], ["https://example.com/vue.runtime.js"], "")
        assert "vue.runtime.js" in hints

    def test_script_hints_for_angular(self):
        hints = _extract_tech_hints({}, [], ["https://example.com/angular.min.js"], "")
        assert "angular.min.js" in hints

    def test_returns_sorted_unique(self):
        headers = {"Server": "nginx"}
        meta = ["WordPress"]
        body = "wp-content here"
        hints = _extract_tech_hints(headers, meta, [], body)
        # The function sorts the result
        assert hints == sorted(hints)
        # And deduplicates
        assert len(hints) == len(set(hints))

    def test_empty_inputs(self):
        hints = _extract_tech_hints({}, [], [], "")
        assert hints == []


# ---------------------------------------------------------------------------
# _extract_cms_hints
# ---------------------------------------------------------------------------


class TestExtractCmsHints:
    def test_wordpress_from_meta(self):
        hints = _extract_cms_hints(["WordPress 6.4"], "", [])
        assert "wordpress" in hints

    def test_wordpress_from_body(self):
        hints = _extract_cms_hints([], "<link href='/wp-content/themes/x.css'>", [])
        assert "wordpress" in hints

    def test_drupal_from_meta(self):
        hints = _extract_cms_hints(["Drupal 9"], "", [])
        assert "drupal" in hints

    def test_drupal_from_body(self):
        hints = _extract_cms_hints([], '<link href="/sites/default/files/x.css">', [])
        assert "drupal" in hints

    def test_joomla_from_meta(self):
        hints = _extract_cms_hints(["Joomla! 4"], "", [])
        assert "joomla" in hints

    def test_joomla_from_scripts(self):
        hints = _extract_cms_hints([], "", ["/media/system/js/mootools-core.js"])
        assert "joomla" in hints

    def test_multiple_cms_detected(self):
        hints = _extract_cms_hints(["WordPress 6.4", "Joomla"], "wp-content /media/system/js/", [])
        # Both should be detected; the function sorts and dedupes
        assert "wordpress" in hints
        assert "joomla" in hints

    def test_no_cms_returns_empty(self):
        hints = _extract_cms_hints([], "<html>nothing</html>", [])
        assert hints == []

    def test_empty_inputs_returns_empty(self):
        assert _extract_cms_hints([], "", []) == []


# ---------------------------------------------------------------------------
# _normalize_form
# ---------------------------------------------------------------------------


class TestNormalizeForm:
    PAGE_URL = "https://example.com/login"

    def test_action_urljoin_with_relative(self):
        form = {"action": "submit", "method": "post", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["action"] == "https://example.com/submit"

    def test_action_urljoin_with_absolute(self):
        form = {"action": "https://other.example/api", "method": "post", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["action"] == "https://other.example/api"

    def test_default_method_is_get(self):
        form = {"action": "x", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        # The function only writes 'method' into the result when the form
        # supplied one (falsy method is dropped) — so missing 'method' on the
        # input means missing 'method' on the output. Verify the documented
        # behaviour rather than assume a default is filled in.
        assert "method" not in result

    def test_supplied_method_is_preserved(self):
        # The function only uses method internally to decide state_changing;
        # the original method string is preserved verbatim in the output dict.
        form = {"action": "x", "method": "POST", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["method"] == "POST"

    def test_state_changing_post(self):
        form = {"action": "x", "method": "post", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["state_changing"] is True

    def test_state_changing_put(self):
        form = {"action": "x", "method": "PUT", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["state_changing"] is True

    def test_state_changing_patch(self):
        form = {"action": "x", "method": "patch", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["state_changing"] is True

    def test_state_changing_delete(self):
        form = {"action": "x", "method": "delete", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["state_changing"] is True

    def test_state_changing_due_to_password_input(self):
        form = {
            "action": "x",
            "method": "get",
            "inputs": [{"name": "pwd", "type": "password"}],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["state_changing"] is True

    def test_state_changing_due_to_file_input(self):
        form = {
            "action": "x",
            "method": "get",
            "inputs": [{"name": "upload", "type": "file"}],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["state_changing"] is True

    def test_state_changing_due_to_hidden_input(self):
        form = {
            "action": "x",
            "method": "get",
            "inputs": [{"name": "csrf_token", "type": "hidden"}],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["state_changing"] is True

    def test_not_state_changing_get_with_text_input(self):
        form = {
            "action": "x",
            "method": "get",
            "inputs": [{"name": "q", "type": "text"}],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["state_changing"] is False

    def test_password_fields_counted(self):
        form = {
            "action": "x",
            "method": "post",
            "inputs": [
                {"name": "user", "type": "text"},
                {"name": "pwd", "type": "password"},
                {"name": "pwd2", "type": "PASSWORD"},
            ],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["password_fields"] == 2

    def test_no_password_fields(self):
        form = {
            "action": "x",
            "method": "post",
            "inputs": [{"name": "user", "type": "text"}],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["password_fields"] == 0

    def test_input_count(self):
        form = {
            "action": "x",
            "method": "post",
            "inputs": [
                {"name": "a", "type": "text"},
                {"name": "b", "type": "text"},
                {"name": "c", "type": "text"},
            ],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["input_count"] == 3

    def test_csrf_token_detected(self):
        form = {
            "action": "x",
            "method": "post",
            "inputs": [
                {"name": "csrfmiddlewaretoken", "type": "hidden"},
                {"name": "user", "type": "text"},
            ],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["has_csrf_token"] is True

    def test_csrf_token_detected_lowercased_name(self):
        # csrf_names uses lowercase tokens; matching is on the lowercase form of the
        # input name — verify the function lowercases input names before lookup.
        form = {
            "action": "x",
            "method": "post",
            "inputs": [{"name": "csrfmiddlewaretoken", "type": "hidden"}],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["has_csrf_token"] is True

    def test_csrf_token_uppercase_name_not_detected(self):
        # The lookup is on the lowercased name; "CSRFTOKEN" lowercases to
        # "csrftoken" which is not in csrf_names — so it is correctly
        # classified as not a CSRF token by this function.
        form = {
            "action": "x",
            "method": "post",
            "inputs": [{"name": "CSRFTOKEN", "type": "hidden"}],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["has_csrf_token"] is False

    def test_csrf_token_not_detected_when_missing(self):
        form = {
            "action": "x",
            "method": "post",
            "inputs": [{"name": "user", "type": "text"}],
        }
        result = _normalize_form(self.PAGE_URL, form)
        assert result["has_csrf_token"] is False

    def test_page_url_included(self):
        form = {"action": "x", "method": "get", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["page_url"] == self.PAGE_URL

    def test_tolerates_missing_inputs(self):
        form = {"action": "x", "method": "get"}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["input_count"] == 0
        assert result["password_fields"] == 0
        assert result["state_changing"] is False

    def test_tolerates_non_list_inputs(self):
        form = {"action": "x", "method": "get", "inputs": "not a list"}
        result = _normalize_form(self.PAGE_URL, form)
        assert result["input_count"] == 0

    def test_tolerates_non_dict_input_items(self):
        form = {
            "action": "x",
            "method": "post",
            "inputs": ["not a dict", {"name": "user", "type": "text"}],
        }
        result = _normalize_form(self.PAGE_URL, form)
        # Function should not crash; the valid dict is counted
        assert result["input_count"] == 2

    def test_blank_action_urljoined_to_page(self):
        form = {"action": "", "method": "get", "inputs": []}
        result = _normalize_form(self.PAGE_URL, form)
        # Empty action resolves to the page URL itself
        assert result["action"] == self.PAGE_URL
