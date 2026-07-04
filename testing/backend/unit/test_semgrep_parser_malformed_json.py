"""
Malformed JSON fallback tests for Semgrep scanner parser (issue #1658).

Tests verify the parser handles various malformed input types gracefully.
These tests import the parser directly, avoiding the FastAPI/aiosqlite import chain.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PARTS = Path(__file__).parts
BASE = Path(*PARTS[: PARTS.index("testing")])
PLUGIN_ID = "semgrep_scanner"
PARSER_PATH = BASE / "plugins" / PLUGIN_ID / "parser.py"


def _load_semgrep_parser():
    spec = importlib.util.spec_from_file_location("semgrep_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_semgrep_parser_truncated_json():
    """Truncated JSON is handled gracefully with empty findings."""
    parser = _load_semgrep_parser()
    parsed = parser.parse('{"results": [{"check_id": "rule-1"')
    assert parsed["count"] == 0
    assert parsed["findings"] == []


def test_semgrep_parser_mixed_stdout_json_fragment():
    """Mixed stdout with a JSON fragment is treated as plain text."""
    parser = _load_semgrep_parser()
    raw = "Starting semgrep scan...\n{\"results\": []}\nDone."
    parsed = parser.parse(raw)
    assert parsed["count"] == 0


def test_semgrep_parser_valid_json_missing_results_key():
    """Valid JSON without 'results' key returns empty findings."""
    parser = _load_semgrep_parser()
    parsed = parser.parse('{"errors": [], "summary": "done"}')
    assert parsed["count"] == 0
    assert parsed["findings"] == []


def test_semgrep_parser_null_in_extra():
    """Null values in extra cause the finding to be silently dropped."""
    parser = _load_semgrep_parser()
    json_data = json.dumps({
        "results": [{
            "check_id": None,
            "path": None,
            "start": None,
            "extra": None,
        }]
    })
    parsed = parser.parse(json_data)
    # Should not crash; finding is dropped because extra=None causes AttributeError
    assert parsed["count"] == 0
    assert parsed["findings"] == []


def test_semgrep_parser_empty_results_array():
    """Valid JSON with empty results array returns zero findings."""
    parser = _load_semgrep_parser()
    parsed = parser.parse('{"results": []}')
    assert parsed["count"] == 0
    assert parsed["findings"] == []


def test_semgrep_parser_non_json_stdout():
    """Completely non-JSON output returns empty findings."""
    parser = _load_semgrep_parser()
    parsed = parser.parse("This is not JSON data at all")
    assert parsed["count"] == 0
    assert parsed["findings"] == []
