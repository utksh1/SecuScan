"""Parser and contract coverage for plugins/wpscan."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# Derive the plugins directory relative to this test file.
# testing/backend/unit/ -> testing/backend/ -> testing/ -> <repo root> -> plugins/
_PLUGINS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "plugins"
PARSER_PATH = _PLUGINS_DIR / "wpscan" / "parser.py"


def _load_wpscan_parser():
    spec = importlib.util.spec_from_file_location("wpscan_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wpscan_parser_valid_json_interesting_findings():
    parser = _load_wpscan_parser()
    data = {
        "interesting_findings": [
            {
                "to_s": "Test WordPress Finding",
                "references": {"url": "https://example.com/advisory"},
            }
        ]
    }
    parsed = parser.parse(json.dumps(data))
    assert parsed["count"] == 1
    assert len(parsed["findings"]) == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "Test WordPress Finding"
    assert finding["category"] == "CMS Exposure"
    assert finding["severity"] == "low"
    assert finding["metadata"]["references"]["url"] == "https://example.com/advisory"


def test_wpscan_parser_valid_json_plugin_vulnerabilities():
    parser = _load_wpscan_parser()
    data = {
        "plugins": {
            "my-plugin": {
                "vulnerabilities": [
                    {
                        "title": "Remote Code Execution",
                        "fixed_in": "2.0.0",
                        "references": {"url": "https://example.com/cve"},
                    }
                ]
            }
        }
    }
    parsed = parser.parse(json.dumps(data))
    assert parsed["count"] == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "WordPress Plugin Vulnerability: my-plugin"
    assert finding["category"] == "CMS Vulnerability"
    assert finding["severity"] == "high"
    assert finding["metadata"]["component"] == "my-plugin"
    assert finding["metadata"]["component_type"] == "plugin"
    assert finding["metadata"]["fixed_in"] == "2.0.0"


def test_wpscan_parser_valid_json_theme_vulnerabilities():
    parser = _load_wpscan_parser()
    data = {
        "themes": {
            "my-theme": {
                "vulnerabilities": [
                    {
                        "title": "XSS Vulnerability",
                        "fixed_in": "1.5.0",
                        "references": {},
                    }
                ]
            }
        }
    }
    parsed = parser.parse(json.dumps(data))
    assert parsed["count"] == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "WordPress Theme Vulnerability: my-theme"
    assert finding["category"] == "CMS Vulnerability"
    assert finding["severity"] == "high"
    assert finding["metadata"]["component_type"] == "theme"


def test_wpscan_parser_text_fallback_on_invalid_json():
    parser = _load_wpscan_parser()
    text_output = "WordPress version 5.8 detected\nPlugin list returned empty"
    parsed = parser.parse(text_output)
    assert parsed["count"] == 2
    assert len(parsed["findings"]) == 2
    for finding in parsed["findings"]:
        assert finding["severity"] == "low"
        assert finding["category"] == "CMS Security"
        assert finding["metadata"]["source"] == "stdout"


def test_wpscan_parser_empty_output():
    parser = _load_wpscan_parser()
    parsed = parser.parse("")
    assert parsed["count"] == 0
    assert parsed["findings"] == []


def test_wpscan_parser_json_with_missing_optional_fields():
    parser = _load_wpscan_parser()
    data = {"plugins": None, "themes": None, "interesting_findings": []}
    parsed = parser.parse(json.dumps(data))
    assert parsed["count"] == 0
    assert parsed["findings"] == []
