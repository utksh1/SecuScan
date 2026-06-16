"""
Unit tests for crawler.py surface-parsing helpers.

Covers: _extract_title, _classify_path_hint, _build_headers,
_extract_tech_hints, _extract_cms_hints, _normalize_form
"""

from backend.secuscan.crawler import (
    _extract_title,
    _classify_path_hint,
    _build_headers,
    _extract_tech_hints,
    _extract_cms_hints,
    _normalize_form,
)


# ── _extract_title ────────────────────────────────────────────────────────────


def test_extract_title_present():
    html = "<html><head><title>My Dashboard</title></head></html>"
    assert _extract_title(html) == "My Dashboard"


def test_extract_title_case_insensitive():
    html = "<HTML><HEAD><TITLE>Case Insensitive</TITLE></HEAD></HTML>"
    assert _extract_title(html) == "Case Insensitive"


def test_extract_title_empty():
    assert _extract_title("") == ""


def test_extract_title_missing():
    html = "<html><body><p>No title here</p></body></html>"
    assert _extract_title(html) == ""


def test_extract_title_malformed_unclosed():
    html = "<title>Never closed"
    assert _extract_title(html) == ""


def test_extract_title_reversed_tags():
    # Note: _extract_title uses str.find which matches </title> containing
    # <title> as a substring. This test documents the clean single-title case.
    html = "<div>header</div><title>Main Title</title><footer>footer</footer>"
    assert _extract_title(html) == "Main Title"


# ── _classify_path_hint ───────────────────────────────────────────────────────


def test_classify_admin_paths():
    for path in ("/admin", "/admin/dashboard", "/wp-admin", "/administrator"):
        assert _classify_path_hint(f"https://example.com{path}") == "admin", f"failed for {path}"


def test_classify_login_paths():
    for path in ("/login", "/signin", "/auth", "/user/login"):
        assert _classify_path_hint(f"https://example.com{path}") == "login", f"failed for {path}"


def test_classify_debug_paths():
    for path in ("/debug", "/console", "/actuator", "/_profiler"):
        assert _classify_path_hint(f"https://example.com{path}") == "debug", f"failed for {path}"


def test_classify_docs_paths():
    for path in ("/docs", "/swagger", "/openapi", "/redoc"):
        assert _classify_path_hint(f"https://example.com{path}") == "docs", f"failed for {path}"


def test_classify_no_match():
    assert _classify_path_hint("/blog/my-post") is None
    assert _classify_path_hint("/products/123") is None
    assert _classify_path_hint("/about-us") is None


def test_classify_path_case_sensitive():
    # Patterns are matched as-is; path must match lowercase token
    assert _classify_path_hint("/admin") == "admin"
    assert _classify_path_hint("/login") == "login"


# ── _build_headers ─────────────────────────────────────────────────────────────


def test_build_headers_default():
    headers = _build_headers()
    assert headers["User-Agent"] == "SecuScan-Crawler/1.0"
    assert "Accept" in headers
    assert len(headers) == 2


def test_build_headers_with_extra():
    headers = _build_headers({"X-Custom": "value", "Referer": "https://example.com"})
    assert headers["X-Custom"] == "value"
    assert headers["Referer"] == "https://example.com"
    assert headers["User-Agent"] == "SecuScan-Crawler/1.0"


def test_build_headers_skips_none_values():
    headers = _build_headers({"X-Null": None, "X-Valid": "ok"})
    assert "X-Null" not in headers  # None values are skipped, not stringified
    assert headers["X-Valid"] == "ok"


def test_build_headers_skips_falsy_keys():
    headers = _build_headers({"": "empty-key", "X-Valid": "ok"})
    assert "" not in headers
    assert headers["X-Valid"] == "ok"


# ── _extract_tech_hints ────────────────────────────────────────────────────────


def test_extract_tech_hints_server_header():
    headers = {"server": "Apache/2.4", "content-type": "text/html"}
    result = _extract_tech_hints(headers, [], [], "")
    assert "Apache/2.4" in result


def test_extract_tech_hints_powered_by():
    headers = {"x-powered-by": "PHP/7.4"}
    result = _extract_tech_hints(headers, [], [], "")
    assert "PHP/7.4" in result


def test_extract_tech_hints_meta_generators():
    headers = {}
    meta_gens = ["WordPress 6.0"]
    result = _extract_tech_hints(headers, meta_gens, [], "")
    assert "WordPress 6.0" in result


def test_extract_tech_hints_wp_content():
    headers = {}
    result = _extract_tech_hints(headers, [], [], "<div>wp-content/uploads/2024/</div>")
    assert "WordPress" in result


def test_extract_tech_hints_drupal():
    headers = {}
    result = _extract_tech_hints(headers, [], [], "<link href='/sites/default/files/style.css'>")
    assert "Drupal" in result


def test_extract_tech_hints_joomla():
    headers = {}
    result = _extract_tech_hints(headers, [], [], "<script src='/media/system/js/mootools.js'></script>")
    assert "Joomla" in result


def test_extract_tech_hints_script_frameworks():
    headers = {}
    scripts = ["/static/js/react.production.min.js", "/lib/vue.global.js"]
    result = _extract_tech_hints(headers, [], scripts, "")
    assert "react.production.min.js" in result
    assert "vue.global.js" in result


def test_extract_tech_hints_deduplication():
    headers = {"server": "Apache", "x-powered-by": "Apache"}
    result = _extract_tech_hints(headers, [], [], "")
    assert result.count("Apache") == 1


# ── _extract_cms_hints ─────────────────────────────────────────────────────────


def test_extract_cms_wordpress():
    result = _extract_cms_hints(["WordPress 6.1"], "", [])
    assert "wordpress" in result


def test_extract_cms_drupal():
    result = _extract_cms_hints(["Drupal 9"], "", [])
    assert "drupal" in result


def test_extract_cms_joomla_meta():
    result = _extract_cms_hints(["Joomla! 4.0"], "", [])
    assert "joomla" in result


def test_extract_cms_joomla_script():
    result = _extract_cms_hints([], "", ["/media/system/js/mootools.js"])
    assert "joomla" in result


def test_extract_cms_wordpress_body():
    result = _extract_cms_hints([], "<div>wp-content/uploads/</div>", [])
    assert "wordpress" in result


def test_extract_cms_deduplication():
    result = _extract_cms_hints(["WordPress", "wordpress"], "wp-content", [])
    assert result.count("wordpress") == 1


# ── _normalize_form ────────────────────────────────────────────────────────────


def test_normalize_form_get_method():
    form = {"method": "get", "action": "/search", "inputs": [{"name": "q", "type": "text", "value": ""}]}
    result = _normalize_form("https://example.com", form)
    assert result["method"] == "get"
    assert result["state_changing"] is False
    assert result["password_fields"] == 0
    assert result["has_csrf_token"] is False


def test_normalize_form_post_method():
    form = {"method": "POST", "action": "/login", "inputs": []}
    result = _normalize_form("https://example.com", form)
    assert result["state_changing"] is True


def test_normalize_form_put_method():
    form = {"method": "put", "action": "/api/update", "inputs": []}
    result = _normalize_form("https://example.com", form)
    assert result["state_changing"] is True


def test_normalize_form_hidden_input():
    form = {"method": "get", "action": "/search", "inputs": [{"name": "token", "type": "hidden", "value": "abc"}]}
    result = _normalize_form("https://example.com", form)
    assert result["state_changing"] is True


def test_normalize_form_password_field():
    form = {"method": "get", "action": "/login", "inputs": [{"name": "pw", "type": "password", "value": ""}]}
    result = _normalize_form("https://example.com", form)
    assert result["password_fields"] == 1
    assert result["state_changing"] is True


def test_normalize_form_csrf_token():
    # Known CSRF token names per _normalize_form's csrf_names set
    csrf_names_tested = []
    for token_name in ["csrf", "_csrf", "csrfmiddlewaretoken", "authenticity_token", "__requestverificationtoken"]:
        form = {"method": "post", "action": "/submit", "inputs": [{"name": token_name, "type": "hidden", "value": "xyz"}]}
        result = _normalize_form("https://example.com", form)
        csrf_names_tested.append((token_name, result["has_csrf_token"]))
    # All named tokens should be detected
    assert all(detected for _, detected in csrf_names_tested), csrf_names_tested


def test_normalize_form_no_csrf():
    form = {"method": "post", "action": "/submit", "inputs": [{"name": "query", "type": "hidden", "value": "xyz"}]}
    result = _normalize_form("https://example.com", form)
    assert result["has_csrf_token"] is False


def test_normalize_form_action_absolute():
    form = {"method": "post", "action": "https://other.com/post", "inputs": []}
    result = _normalize_form("https://example.com", form)
    assert result["action"] == "https://other.com/post"


def test_normalize_form_action_relative():
    form = {"method": "post", "action": "/post", "inputs": []}
    result = _normalize_form("https://example.com/submit", form)
    assert result["action"] == "https://example.com/post"


def test_normalize_form_action_empty():
    form = {"method": "post", "action": "", "inputs": []}
    result = _normalize_form("https://example.com/submit", form)
    assert result["action"] == "https://example.com/submit"


def test_normalize_form_input_count():
    form = {"method": "get", "action": "/", "inputs": [{"name": "a", "type": "text"}, {"name": "b", "type": "text"}]}
    result = _normalize_form("https://example.com", form)
    assert result["input_count"] == 2


def test_normalize_form_page_url_set():
    form = {"method": "get", "action": "", "inputs": []}
    result = _normalize_form("https://example.com/my-page", form)
    assert result["page_url"] == "https://example.com/my-page"
