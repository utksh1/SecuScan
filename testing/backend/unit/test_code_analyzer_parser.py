import json
from plugins.code_analyzer.parser import parse


def test_code_analyzer_parser_normal_output():
    # A sample output representing a normal Bandit JSON output
    normal_output = json.dumps({
        "results": [
            {
                "code": "import pickle\npickle.loads(user_input)",
                "filename": "server.py",
                "issue_confidence": "HIGH",
                "issue_severity": "HIGH",
                "issue_text": "Deserialize untrusted data using pickle",
                "line_number": 12,
                "line_range": [12],
                "more_info": "https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html#b301-pickle",
                "test_id": "B301",
                "test_name": "blacklist"
            },
            {
                "code": "print('Hello')",
                "filename": "hello.py",
                "issue_confidence": "LOW",
                "issue_severity": "LOW",
                "issue_text": "Some minor warning",
                "line_number": 5,
                "line_range": [5],
                "more_info": "https://bandit.readthedocs.io/some-warning",
                "test_id": "B100",
                "test_name": "minor"
            }
        ]
    })

    result = parse(normal_output)

    assert result["count"] == 2
    assert len(result["findings"]) == 2

    # Verify first finding
    f1 = result["findings"][0]
    assert f1["title"] == "Bandit issue: Deserialize untrusted data using pickle in server.py"
    assert f1["category"] == "Code Security"
    assert f1["severity"] == "high"
    assert "Severity: high, Confidence: high." in f1["description"]
    assert "Found in server.py at line 12." in f1["description"]
    assert f1["remediation"] == "Review the affected code and follow secure coding practices."
    assert f1["metadata"]["issue_text"] == "Deserialize untrusted data using pickle"
    assert f1["metadata"]["file"] == "server.py"
    assert f1["metadata"]["line"] == 12
    assert f1["metadata"]["test_id"] == "B301"
    assert f1["metadata"]["more_info"] == "https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html#b301-pickle"

    # Verify second finding
    f2 = result["findings"][1]
    assert f2["title"] == "Bandit issue: Some minor warning in hello.py"
    assert f2["severity"] == "low"
    assert "Confidence: low" in f2["description"]


def test_code_analyzer_parser_empty_output():
    # Empty string should not crash and should return empty results
    result = parse("")
    assert result == {"findings": [], "count": 0}


def test_code_analyzer_parser_malformed_json():
    # Malformed JSON should not crash and should return empty results
    result = parse("{ malformed json }")
    assert result == {"findings": [], "count": 0}


def test_code_analyzer_parser_missing_results_key():
    # Valid JSON but missing "results" key
    result = parse("{}")
    assert result == {"findings": [], "count": 0}


def test_code_analyzer_parser_missing_fields_in_results():
    # "results" list contains objects with missing fields
    partial_output = json.dumps({
        "results": [
            {
                # missing filename, line_number, issue_severity, issue_confidence, test_id, more_info
                "issue_text": "Insecure function call"
            }
        ]
    })

    result = parse(partial_output)

    assert result["count"] == 1
    assert len(result["findings"]) == 1

    finding = result["findings"][0]
    assert finding["title"] == "Bandit issue: Insecure function call in Unknown"
    assert finding["severity"] == "low"
    assert "Confidence: low" in finding["description"]
    assert "Found in Unknown at line 0." in finding["description"]
    assert finding["metadata"]["test_id"] == "unknown"
    assert finding["metadata"]["more_info"] == ""
