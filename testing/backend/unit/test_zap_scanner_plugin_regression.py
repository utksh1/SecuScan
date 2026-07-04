"""
Regression tests for ZAP plugin output handling (issue #1657).

Tests verify the parser's behavior on placeholder content and edge cases.
The parser treats every non-empty line as a potential finding.
"""
from __future__ import annotations

from pathlib import Path

import importlib.util

PARTS = Path(__file__).parts
BASE = Path(*PARTS[: PARTS.index("testing")])
PLUGIN_ID = "zap_scanner"
PARSER_PATH = BASE / "plugins" / PLUGIN_ID / "parser.py"


def _load_zap_scanner_parser():
    spec = importlib.util.spec_from_file_location("zap_scanner_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_zap_scanner_parser_placeholder_not_high_severity():
    """Placeholder scan string is not classified as high or critical severity."""
    parser = _load_zap_scanner_parser()
    parsed = parser.parse("ZAP connector placeholder scan")
    assert parsed["count"] == 1
    # Not high/critical — no attack-related keywords in the placeholder
    high_findings = [
        f for f in parsed["findings"]
        if f["severity"] in ("high", "critical")
    ]
    assert high_findings == [], (
        f"Placeholder should not appear as high-severity: {high_findings}"
    )


def test_zap_scanner_parser_real_high_severity_keywords():
    """Lines containing 'injection' are classified as high severity."""
    parser = _load_zap_scanner_parser()
    parsed = parser.parse("FAIL-NEW: SQL Injection found in login form")
    assert parsed["count"] == 1
    assert parsed["findings"][0]["severity"] == "high"


def test_zap_scanner_parser_real_low_severity_keywords():
    """Lines containing 'warning' or 'detected' are classified as low severity."""
    parser = _load_zap_scanner_parser()
    parsed = parser.parse("WARN: X-Frame-Options header missing detected")
    assert parsed["count"] == 1
    assert parsed["findings"][0]["severity"] == "low"


def test_zap_scanner_parser_empty_string_returns_empty():
    """Empty input returns zero findings."""
    parser = _load_zap_scanner_parser()
    parsed = parser.parse("")
    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["items"] == []


def test_zap_scanner_parser_whitespace_only_returns_empty():
    """Whitespace-only input returns zero findings."""
    parser = _load_zap_scanner_parser()
    parsed = parser.parse("   \n  \n   ")
    assert parsed["findings"] == []
    assert parsed["count"] == 0
