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
    valid_json = json.dumps({
        "results": [
            {
                "check_id": "rule-1",
                "path": "src/main.py",
                "start": {"line": 42},
                "extra": {
                    "message": "Found an issue",
                    "severity": "ERROR",
                    "lines": "eval(user_input)"
                }
            }
        ]
    })
    
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
    missing_fields_json = json.dumps({
        "results": [
            {
                # Missing check_id, path, start, extra
            }
        ]
    })
    
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
        json_data = json.dumps({
            "results": [
                {
                    "extra": {
                        "severity": semgrep_sev
                    }
                }
            ]
        })
        
        parsed = parser.parse(json_data)
        assert parsed["findings"][0]["severity"] == expected_secuscan_sev
