"""Parser and contract coverage for plugins/semgrep_scanner."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "semgrep_scanner"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_semgrep_parser():
    spec = importlib.util.spec_from_file_location("semgrep_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_semgrep_parser_valid_json():
    parser = _load_semgrep_parser()
    valid_json = json.dumps(
        {
            "results": [
                {
                    "check_id": "rule-1",
                    "path": "src/main.py",
                    "start": {"line": 42},
                    "extra": {
                        "message": "Found an issue",
                        "severity": "ERROR",
                        "lines": "eval(user_input)",
                    },
                }
            ]
        }
    )

    parsed = parser.parse(valid_json)
    assert parsed["count"] == 1
    assert len(parsed["findings"]) == 1

    finding = parsed["findings"][0]
    assert finding["title"] == "Semgrep issue: rule-1 in src/main.py"
    assert finding["severity"] == "high"
    assert finding["description"] == "Found an issue"
    assert finding["metadata"]["rule_id"] == "rule-1"
    assert finding["metadata"]["file"] == "src/main.py"
    assert finding["metadata"]["line"] == 42
    assert finding["metadata"]["evidence"] == "eval(user_input)"
    assert finding["metadata"]["semgrep_severity"] == "ERROR"


def test_semgrep_parser_invalid_json():
    parser = _load_semgrep_parser()
    invalid_json = "This is not JSON data"

    parsed = parser.parse(invalid_json)
    assert parsed["count"] == 0
    assert parsed["findings"] == []


def test_semgrep_parser_missing_fields():
    parser = _load_semgrep_parser()
    missing_fields_json = json.dumps(
        {
            "results": [
                {
                    # Missing check_id, path, start, extra
                }
            ]
        }
    )

    parsed = parser.parse(missing_fields_json)
    assert parsed["count"] == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "Semgrep issue: Unknown Rule in Unknown Path"
    assert finding["description"] == "No message provided"
    assert finding["severity"] == "info"
    assert finding["metadata"]["rule_id"] == "Unknown Rule"
    assert finding["metadata"]["file"] == "Unknown Path"
    assert finding["metadata"]["line"] == 0
    assert finding["metadata"]["evidence"] == ""
    assert finding["metadata"]["semgrep_severity"] == "INFO"


def test_semgrep_parser_severity_mapping():
    parser = _load_semgrep_parser()
    test_cases = [
        ("INFO", "info"),
        ("WARNING", "medium"),
        ("ERROR", "high"),
        ("UNKNOWN_SEVERITY", "low"),
    ]

    for semgrep_sev, expected_secuscan_sev in test_cases:
        json_data = json.dumps({"results": [{"extra": {"severity": semgrep_sev}}]})

        parsed = parser.parse(json_data)
        assert parsed["findings"][0]["severity"] == expected_secuscan_sev


class TestSemgrepParserMalformedJsonFallback:
    """
    Verify the Semgrep parser's silent fallback behaviour when JSON is malformed.

    The parser wraps all parsing in ``except Exception: pass``, so every
    malformed-input variant must deterministically return
    ``{"count": 0, "findings": []}``.
    """

    def test_truncated_json_returns_empty_findings(self):
        """Truncated JSON (open object never closed) must return count=0, findings=[].

        Simulates a scanner process that was killed mid-write, leaving an
        incomplete JSON payload in stdout.
        """
        parser = _load_semgrep_parser()
        truncated = '{"results": [{'

        parsed = parser.parse(truncated)

        assert parsed["count"] == 0
        assert parsed["findings"] == []

    def test_mixed_stdout_with_json_fragment_returns_deterministic_empty_result(self):
        """Mixed stdout containing log lines + a JSON fragment must return count=0.

        Real Semgrep invocations may print warning/info lines to stdout before
        the JSON block.  If the full stdout is fed to the parser the result
        must still be a deterministic empty-findings dict, not a crash.
        """
        parser = _load_semgrep_parser()
        mixed_stdout = (
            "Running semgrep...\n"
            "Loading rules from registry...\n"
            '{"results": [{"check_id": "rule-x"'  # fragment — never closed
        )

        parsed = parser.parse(mixed_stdout)

        assert parsed["count"] == 0
        assert parsed["findings"] == []
        # Call twice to confirm determinism
        parsed_again = parser.parse(mixed_stdout)
        assert parsed_again["count"] == 0
        assert parsed_again["findings"] == []

    def test_valid_json_missing_top_level_results_key_returns_empty(self):
        """Valid JSON that lacks the top-level ``results`` key must return count=0.

        The parser calls ``data.get("results", [])``, so missing the key
        should yield an empty findings list rather than raise.
        """
        parser = _load_semgrep_parser()
        no_results_key = json.dumps({"version": "1.0", "errors": []})

        parsed = parser.parse(no_results_key)

        assert parsed["count"] == 0
        assert parsed["findings"] == []

    def test_valid_json_with_null_in_critical_fields_returns_empty_without_crash(self):
        """Null values in critical fields must not raise and must return count=0.

        Some Semgrep builds (or mocked environments) can emit ``null`` for
        ``results`` itself.  The parser must absorb this gracefully because
        ``null`` is valid JSON but iteration over it raises ``TypeError``,
        which the broad ``except Exception`` clause catches.
        """
        parser = _load_semgrep_parser()
        null_results = json.dumps({"results": None})

        parsed = parser.parse(null_results)

        assert parsed["count"] == 0
        assert parsed["findings"] == []
