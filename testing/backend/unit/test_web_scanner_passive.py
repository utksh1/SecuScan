from backend.secuscan.scanners.web_scanner import WebScanner


def test_web_scanner_passive_findings_cover_headers_cookies_forms_and_paths():
    scanner = WebScanner(task_id="test-task", db=None)
    crawl = {
        "final_url": "http://example.com/login",
        "seed_url": "http://example.com",
        "scheme": "http",
        "headers": {"server": "nginx"},
        "set_cookie_headers": ["sessionid=abc123; Path=/"],
        "forms": [
            {
                "action": "http://example.com/login",
                "method": "post",
                "state_changing": True,
                "has_csrf_token": False,
                "password_fields": 1,
            }
        ],
        "path_hints": [
            {"url": "http://example.com/admin", "kind": "admin"},
            {"url": "http://example.com/docs", "kind": "docs"},
        ],
        "cms_hints": ["wordpress"],
        "api_hints": ["http://example.com/openapi.json"],
        "pages": [],
    }

    findings = scanner._build_passive_findings("http://example.com", crawl)
    titles = {item["title"] for item in findings}

    assert "Missing Content-Security-Policy" in titles
    assert "Insecure Cookie Attributes on sessionid" in titles
    assert "State-Changing Form Missing CSRF Indicators: http://example.com/login" in titles
    assert "Credential Form Exposed over Non-HTTPS: http://example.com/login" in titles
    assert "Administrative Paths Exposed" in titles
    assert "CMS Fingerprint Detected: Wordpress" in titles
