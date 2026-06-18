"""
Tests for backend.secuscan.crawler pure parse/extract helper functions.

Covers:
- _build_headers: default headers and extra_headers merging
- _extract_title: valid, missing, and malformed HTML
- _normalize_form: GET/POST forms, CSRF tokens, password fields
- _classify_path_hint: admin/login/debug/docs/unknown paths
- _extract_tech_hints: server headers, CMS body patterns, JS libraries
- _extract_cms_hints: meta generators and body patterns
- _SurfaceParser: HTML feed collecting links, scripts, forms, meta generators
"""

from backend.secuscan.crawler_helpers import (
    _build_headers,
    _extract_title,
    _normalize_form,
    _classify_path_hint,
    _extract_tech_hints,
    _extract_cms_hints,
    _SurfaceParser,
)


class TestBuildHeaders:
    def test_returns_default_headers(self):
        headers = _build_headers(None)
        assert headers["User-Agent"] == "SecuScan-Crawler/1.0"
        assert "text/html" in headers["Accept"]

    def test_extra_headers_merged(self):
        headers = _build_headers({"X-Custom": "value", "Referer": "http://example.com"})
        assert headers["X-Custom"] == "value"
        assert headers["Referer"] == "http://example.com"
        assert headers["User-Agent"] == "SecuScan-Crawler/1.0"

    def test_non_string_values_converted_to_string(self):
        headers = _build_headers({"X-Count": 42, "X-Active": True})
        assert headers["X-Count"] == "42"
        assert headers["X-Active"] == "True"

    def test_empty_extra_headers_ignored(self):
        headers = _build_headers({})
        assert "User-Agent" in headers


class TestExtractTitle:
    def test_extracts_title_text(self):
        html = "<html><head><title>My Page Title</title></head></html>"
        assert _extract_title(html) == "My Page Title"

    def test_title_case_insensitive(self):
        html = "<HTML><HEAD><TITLE>Hello</TITLE></HEAD></HTML>"
        assert _extract_title(html) == "Hello"

    def test_no_title_tag_returns_empty(self):
        html = "<html><body>No title here</body></html>"
        assert _extract_title(html) == ""

    def test_malformed_title_returns_empty(self):
        assert _extract_title("<title>unclosed") == ""
        assert _extract_title("</title>no start") == ""


class TestNormalizeForm:
    def test_get_form_not_state_changing(self):
        form = {
            "action": "",
            "method": "get",
            "inputs": [{"name": "q", "type": "text", "value": ""}],
        }
        result = _normalize_form("http://example.com/page", form)
        assert result["state_changing"] is False
        assert result["has_csrf_token"] is False
        assert result["password_fields"] == 0

    def test_post_form_is_state_changing(self):
        form = {
            "action": "",
            "method": "post",
            "inputs": [{"name": "data", "type": "text", "value": "test"}],
        }
        result = _normalize_form("http://example.com/page", form)
        assert result["state_changing"] is True

    def test_form_with_csrf_token(self):
        form = {
            "action": "",
            "method": "post",
            "inputs": [
                {"name": "csrfmiddlewaretoken", "type": "hidden", "value": "abc123"}
            ],
        }
        result = _normalize_form("http://example.com/page", form)
        assert result["has_csrf_token"] is True

    def test_form_with_password_field(self):
        form = {
            "action": "",
            "method": "post",
            "inputs": [
                {"name": "username", "type": "text", "value": ""},
                {"name": "password", "type": "password", "value": ""},
            ],
        }
        result = _normalize_form("http://example.com/page", form)
        assert result["password_fields"] == 1

    def test_relative_action_resolved(self):
        form = {
            "action": "/submit",
            "method": "post",
            "inputs": [],
        }
        result = _normalize_form("http://example.com/page", form)
        assert result["action"] == "http://example.com/submit"
        assert result["page_url"] == "http://example.com/page"

    def test_form_input_count(self):
        form = {
            "action": "",
            "method": "get",
            "inputs": [{"name": "a", "type": "text"}, {"name": "b", "type": "text"}],
        }
        result = _normalize_form("http://example.com/page", form)
        assert result["input_count"] == 2


class TestClassifyPathHint:
    def test_admin_paths(self):
        for path in ["/admin", "/wp-admin", "/administrator/dashboard"]:
            assert _classify_path_hint(path) == "admin", f"Failed for {path}"

    def test_login_paths(self):
        for path in ["/login", "/signin", "/auth", "/user/login"]:
            assert _classify_path_hint(path) == "login", f"Failed for {path}"

    def test_debug_paths(self):
        for path in ["/debug", "/console", "/actuator/prometheus", "/_profiler"]:
            assert _classify_path_hint(path) == "debug", f"Failed for {path}"

    def test_docs_paths(self):
        for path in ["/docs", "/swagger", "/openapi.json", "/redoc"]:
            assert _classify_path_hint(path) == "docs", f"Failed for {path}"

    def test_unknown_path_returns_none(self):
        assert _classify_path_hint("/random/page") is None
        assert _classify_path_hint("/users/123") is None


class TestExtractTechHints:
    def test_server_header(self):
        headers = {"server": "Apache/2.4"}
        hints = _extract_tech_hints(headers, [], [], "")
        assert "Apache/2.4" in hints

    def test_x_powered_by_header(self):
        headers = {"x-powered-by": "PHP/8.1"}
        hints = _extract_tech_hints(headers, [], [], "")
        assert "PHP/8.1" in hints

    def test_wordpress_body_pattern(self):
        body = "<html><body>wp-content/uploads/2024/image.png</body></html>"
        hints = _extract_tech_hints({}, [], [], body)
        assert "WordPress" in hints

    def test_drupal_body_pattern(self):
        body = '<html><body><img src="/sites/default/files/logo.png"/></body></html>'
        hints = _extract_tech_hints({}, [], [], body)
        assert "Drupal" in hints

    def test_joomla_body_pattern(self):
        body = '<html><body>Joomla! 4.0 CMS</body></html>'
        hints = _extract_tech_hints({}, [], [], body)
        assert "Joomla" in hints

    def test_jquery_script_hint(self):
        scripts = ["/static/js/jquery.min.js"]
        hints = _extract_tech_hints({}, [], scripts, "")
        assert "jquery.min.js" in hints


class TestExtractCmsHints:
    def test_wordpress_meta_generator(self):
        meta = ["WordPress 6.2"]
        hints = _extract_cms_hints(meta, "", [])
        assert "wordpress" in hints

    def test_drupal_meta_generator(self):
        meta = ["Drupal 9"]
        hints = _extract_cms_hints(meta, "", [])
        assert "drupal" in hints

    def test_joomla_script_pattern(self):
        scripts = ["/media/system/js/mootools.js"]
        hints = _extract_cms_hints([], "", scripts)
        assert "joomla" in hints


class TestSurfaceParser:
    def test_collects_links(self):
        parser = _SurfaceParser()
        parser.feed('<a href="/page1">Link1</a><a href="/page2">Link2</a>')
        assert parser.links == ["/page1", "/page2"]

    def test_collects_scripts(self):
        parser = _SurfaceParser()
        parser.feed('<script src="/static/app.js"></script>')
        assert parser.scripts == ["/static/app.js"]

    def test_collects_meta_generators(self):
        parser = _SurfaceParser()
        parser.feed('<meta name="generator" content="WordPress 6.0">')
        assert parser.meta_generators == ["WordPress 6.0"]

    def test_collects_forms(self):
        parser = _SurfaceParser()
        parser.feed(
            '<form action="/submit" method="post" id="login-form">'
            '<input name="username" type="text"/><input name="password" type="password"/>'
            '</form>'
        )
        assert len(parser.forms) == 1
        form = parser.forms[0]
        assert form["method"] == "post"
        assert form["action"] == "/submit"
        assert form["id"] == "login-form"
        assert len(form["inputs"]) == 2

    def test_nested_form_inputs(self):
        parser = _SurfaceParser()
        parser.feed(
            '<form><textarea name="content"></textarea>'
            '<select name="country"><option>US</option></select></form>'
        )
        assert len(parser.forms) == 1
        assert len(parser.forms[0]["inputs"]) == 2

    def test_form_cleared_on_endtag(self):
        parser = _SurfaceParser()
        parser.feed('<form></form><form></form>')
        assert len(parser.forms) == 2
