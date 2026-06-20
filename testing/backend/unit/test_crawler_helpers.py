"""
Unit tests for backend.secuscan.crawler_helpers sync helpers.
The sync helpers were extracted to crawler_helpers.py so they can be imported
and tested without loading httpx.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.crawler_helpers import (
    _build_headers,
    _extract_title,
    _normalize_form,
    _classify_path_hint,
    _extract_tech_hints,
    _extract_cms_hints,
)


class TestBuildHeaders:
    def test_default_headers_present(self):
        headers = _build_headers()
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert headers["User-Agent"] == "SecuScan-Crawler/1.0"

    def test_extra_headers_merged(self):
        headers = _build_headers({"X-Custom": "value", "Authorization": "Bearer token"})
        assert headers["User-Agent"] == "SecuScan-Crawler/1.0"
        assert headers["X-Custom"] == "value"
        assert headers["Authorization"] == "Bearer token"

    def test_none_values_filtered(self):
        headers = _build_headers({"X-Null": None, "X-Valid": "yes"})
        assert "X-Null" not in headers
        assert headers["X-Valid"] == "yes"

    def test_empty_key_filtered(self):
        headers = _build_headers({"": "empty-key-value"})
        assert "" not in headers


class TestExtractTitle:
    def test_extracts_title(self):
        html = "<html><head><title>My Page Title</title></head></html>"
        assert _extract_title(html) == "My Page Title"

    def test_case_insensitive(self):
        html = "<html><head><TITLE>Upper Case</TITLE></head></html>"
        assert _extract_title(html) == "Upper Case"

    def test_no_title_returns_empty(self):
        html = "<html><body>No title here</body></html>"
        assert _extract_title(html) == ""

    def test_unclosed_tag_returns_empty(self):
        html = "<html><head><title>Unclosed"
        assert _extract_title(html) == ""

    def test_empty_html_returns_empty(self):
        assert _extract_title("") == ""

    def test_title_with_whitespace(self):
        html = "<html><head>   <title>   Spaced   </title>   </head></html>"
        assert _extract_title(html) == "Spaced"


class TestNormalizeForm:
    def test_action_url_normalized(self):
        form = {"action": "/submit", "method": "POST", "inputs": []}
        result = _normalize_form("https://example.com/page", form)
        assert result["action"] == "https://example.com/submit"
        assert result["page_url"] == "https://example.com/page"

    def test_state_changing_detected(self):
        post_form = {"action": "", "method": "post", "inputs": []}
        assert _normalize_form("https://example.com", post_form)["state_changing"] is True

    def test_password_field_detected(self):
        form = {"action": "", "method": "post", "inputs": [{"name": "pw", "type": "password"}]}
        result = _normalize_form("https://example.com", form)
        assert result["password_fields"] == 1
        assert result["state_changing"] is True

    def test_csrf_token_detected(self):
        form = {"action": "", "method": "post", "inputs": [{"name": "csrfmiddlewaretoken", "type": "hidden"}]}
        result = _normalize_form("https://example.com", form)
        assert result["has_csrf_token"] is True

    def test_missing_keys_handled(self):
        form = {}
        result = _normalize_form("https://example.com", form)
        assert isinstance(result, dict)
        assert "state_changing" in result


class TestClassifyPathHint:
    def test_admin_paths(self):
        assert _classify_path_hint("/admin/dashboard") == "admin"
        assert _classify_path_hint("/wp-admin/") == "admin"
        assert _classify_path_hint("/administrator/") == "admin"

    def test_login_paths(self):
        assert _classify_path_hint("/login") == "login"
        assert _classify_path_hint("/user/login") == "login"
        assert _classify_path_hint("/signin") == "login"

    def test_debug_paths(self):
        assert _classify_path_hint("/debug") == "debug"
        assert _classify_path_hint("/actuator/health") == "debug"

    def test_docs_paths(self):
        assert _classify_path_hint("/docs") == "docs"
        assert _classify_path_hint("/swagger") == "docs"
        assert _classify_path_hint("/openapi.json") == "docs"

    def test_unknown_returns_none(self):
        assert _classify_path_hint("/random/path") is None
        assert _classify_path_hint("/products/123") is None


class TestExtractTechHints:
    def test_extracts_server_header(self):
        headers = {"server": "nginx/1.20"}
        hints = _extract_tech_hints(headers, [], [], "")
        assert "nginx/1.20" in hints

    def test_extracts_meta_generators(self):
        meta_generators = ["WordPress 6.0"]
        hints = _extract_tech_hints({}, meta_generators, [], "")
        assert "WordPress 6.0" in hints

    def test_extracts_wordpress_from_body(self):
        body = "<html><body>wp-content/plugins/myplugin</body></html>"
        hints = _extract_tech_hints({}, [], [], body)
        assert "WordPress" in hints

    def test_extracts_jquery_from_scripts(self):
        scripts = ["/static/jquery.min.js", "/static/app.js"]
        hints = _extract_tech_hints({}, [], scripts, "")
        assert "jquery.min.js" in hints

    def test_returns_sorted_unique(self):
        headers = {"server": "Apache"}
        scripts = ["/jquery.min.js", "/JQUERY.MIN.JS"]
        hints = _extract_tech_hints(headers, [], scripts, "")
        assert hints == sorted(set(hints))


class TestExtractCmsHints:
    def test_wordpress_from_meta(self):
        hints = _extract_cms_hints(["WordPress 6.0"], "", [])
        assert "wordpress" in hints

    def test_wordpress_from_body(self):
        hints = _extract_cms_hints([], "<html>wp-content</html>", [])
        assert "wordpress" in hints

    def test_drupal_from_meta(self):
        hints = _extract_cms_hints(["Drupal 9"], "", [])
        assert "drupal" in hints

    def test_drupal_from_body(self):
        hints = _extract_cms_hints([], "<html>/sites/default/files</html>", [])
        assert "drupal" in hints

    def test_joomla_from_meta(self):
        hints = _extract_cms_hints(["Joomla! 4.0"], "", [])
        assert "joomla" in hints

    def test_joomla_from_scripts(self):
        scripts = ["/media/system/js/mootools.js"]
        hints = _extract_cms_hints([], "", scripts)
        assert "joomla" in hints

    def test_returns_sorted_unique(self):
        hints = _extract_cms_hints(["WordPress", "WordPress"], "<html>wp-content</html>", [])
        assert hints == sorted(set(hints))
        assert len(hints) == 1
