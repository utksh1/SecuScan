import pytest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from plugins.semgrep_scanner.parser import parse

# Test 1: Valid JSON input
def test_valid_json():
    valid_input = json.dumps({
        "results": [
            {
                "check_id": "python.security.test-rule",
                "path": "app.py",
                "extra": {
                    "message": "Test security issue",
                    "severity": "WARNING",
                    "lines": "eval(user_input)"
                },
                "start": {"line": 10}
            }
        ]
    })
    result = parse(valid_input)
    assert result["count"] == 1
    assert result["findings"][0]["severity"] == "medium"
    assert result["findings"][0]["category"] == "Code Security"

# Test 2: Invalid JSON input
def test_invalid_json():
    invalid_input = "this is not json {{{broken"
    result = parse(invalid_input)
    assert result["count"] == 0
    assert result["findings"] == []

# Test 3: Mixed stdout (JSON mixed with other text)
def test_mixed_stdout():
    mixed_input = "Some random text\n{invalid json here}\nmore text"
    result = parse(mixed_input)
    assert result["count"] == 0
    assert result["findings"] == []