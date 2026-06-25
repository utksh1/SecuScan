"""
Unit tests for _slugify_filename_part and build_report_filename helpers.

Imports the real production functions from backend.secuscan.routes so
a regression in the actual implementation is caught by these tests.
"""

import re
from backend.secuscan.routes_report_helpers import _slugify_filename_part, build_report_filename


# ---------------------------------------------------------------------------
# _slugify_filename_part
# ---------------------------------------------------------------------------


def test_slugify_lowercases():
    """Input is lowercased before slugification."""
    assert _slugify_filename_part("Nmap", "scan") == "nmap"


def test_slugify_replaces_non_alphanumeric_with_dash():
    """Non-alphanumeric characters are replaced with dashes."""
    assert _slugify_filename_part("Hello World!", "scan") == "hello-world"


def test_slugify_collapse_multiple_dashes():
    """Multiple consecutive non-alphanumeric chars collapse to a single dash."""
    assert _slugify_filename_part("hello...world", "scan") == "hello-world"
    assert _slugify_filename_part("a--b--c", "scan") == "a-b-c"


def test_slugify_strips_leading_trailing_dashes():
    """Leading and trailing dashes are stripped."""
    assert _slugify_filename_part("!!!scan!!!", "scan") == "scan"
    assert _slugify_filename_part("--nmap--", "scan") == "nmap"


def test_slugify_returns_fallback_on_empty():
    """Empty result after cleaning returns the fallback string."""
    assert _slugify_filename_part("!!!", "scan") == "scan"
    assert _slugify_filename_part("---", "fallback") == "fallback"


def test_slugify_already_slug():
    """Already-slugified input passes through unchanged."""
    assert _slugify_filename_part("nmap-scanner", "scan") == "nmap-scanner"


def test_slugify_with_underscores():
    """Underscores are treated as non-alphanumeric and replaced with dash."""
    assert _slugify_filename_part("nmap_scanner", "scan") == "nmap-scanner"


def test_slugify_fallback_not_used_when_result_is_valid():
    """Fallback is not returned when there is a valid result."""
    result = _slugify_filename_part("tool", "fallback")
    assert result == "tool"
    assert result != "fallback"


# ---------------------------------------------------------------------------
# build_report_filename
# ---------------------------------------------------------------------------


def test_filename_includes_tool_target_date():
    """Filename follows the pattern secuscan_{tool}_{target}_{date}.{ext}."""
    task = {
        "tool_name": "nmap",
        "target": "example.com",
        "created_at": "2026-06-22T10:00:00Z",
    }
    result = build_report_filename(task, "csv")
    assert result.startswith("secuscan_nmap_example-com_2026-06-22.csv")


def test_filename_uses_plugin_id_when_tool_name_absent():
    """plugin_id is used when tool_name is missing."""
    task = {
        "plugin_id": "nmap",
        "target": "example.com",
        "created_at": "2026-06-22",
    }
    result = build_report_filename(task, "csv")
    assert "nmap" in result
    assert "example-com" in result
    assert result.endswith(".csv")


def test_filename_uses_scan_fallback_for_missing_tool():
    """scan is used as tool fallback when both tool_name and plugin_id are absent."""
    task = {
        "target": "example.com",
        "created_at": "2026-06-22",
    }
    result = build_report_filename(task, "csv")
    assert result.startswith("secuscan_scan_")


def test_filename_strips_scheme_from_target():
    """The scheme (http://) is stripped from target."""
    task = {
        "tool_name": "nmap",
        "target": "http://example.com",
        "created_at": "2026-06-22",
    }
    result = build_report_filename(task, "csv")
    assert "http://" not in result
    assert "example-com" in result


def test_filename_uses_netloc_for_full_url():
    """Netloc is extracted from full URL targets."""
    task = {
        "tool_name": "nmap",
        "target": "https://app.example.com/path",
        "created_at": "2026-06-22",
    }
    result = build_report_filename(task, "csv")
    assert "app-example-com" in result


def test_filename_uses_path_for_scheme_less_url():
    """Path is used when target has no scheme."""
    task = {
        "tool_name": "nmap",
        "target": "example.com",
        "created_at": "2026-06-22",
    }
    result = build_report_filename(task, "csv")
    assert "example-com" in result


def test_filename_uses_report_fallback_when_no_date():
    """report is used when created_at is missing."""
    task = {
        "tool_name": "nmap",
        "target": "example.com",
    }
    result = build_report_filename(task, "csv")
    assert "_report." in result


def test_filename_uses_report_fallback_when_date_not_iso_format():
    """report is used when created_at does not contain an ISO date."""
    task = {
        "tool_name": "nmap",
        "target": "example.com",
        "created_at": "not-a-date",
    }
    result = build_report_filename(task, "csv")
    assert "_report." in result


def test_filename_handles_html_extension():
    """html extension is appended correctly."""
    task = {"tool_name": "nmap", "target": "example.com", "created_at": "2026-06-22"}
    result = build_report_filename(task, "html")
    assert result.endswith(".html")


def test_filename_handles_pdf_extension():
    """pdf extension is appended correctly."""
    task = {"tool_name": "nmap", "target": "example.com", "created_at": "2026-06-22"}
    result = build_report_filename(task, "pdf")
    assert result.endswith(".pdf")


def test_filename_handles_sarif_extension():
    """sarif extension is appended correctly."""
    task = {"tool_name": "nmap", "target": "example.com", "created_at": "2026-06-22"}
    result = build_report_filename(task, "sarif")
    assert result.endswith(".sarif")


def test_filename_target_fallback():
    """target is used as target fallback when target is empty."""
    task = {
        "tool_name": "nmap",
        "target": "",
        "created_at": "2026-06-22",
    }
    result = build_report_filename(task, "csv")
    assert "_target_" in result


def test_filename_contains_only_safe_chars():
    """Output contains only lowercase alphanumerics, underscores, hyphens, dots."""
    task = {
        "tool_name": "Nikto",
        "target": "https://example.com/",
        "created_at": "2026-06-22",
    }
    result = build_report_filename(task, "csv")
    assert re.match(r"^[a-z0-9_.\-]+$", result)
