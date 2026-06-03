import json
import pytest
from backend.secuscan.reporting import reporting

@pytest.fixture
def sample_scan_data():
    task = {
        "id": "task_abc123",
        "tool_name": "TestScanner",
        "target": "https://example.com",
        "status": "completed",
        "created_at": "2026-05-31T12:00:00Z",
        "preset": "default"
    }
    result = {
        "findings": [
            {
                "title": "Reflected Cross-Site Scripting",
                "severity": "HIGH",
                "category": "Injection",
                "description": "User input is reflected without sanitization.",
                "remediation": "Escape all user-supplied input.",
                "proof": "<script>alert(1)</script>",
                "cve": "CVE-2024-0001",
                "target": "https://example.com/search"
            }
        ],
        "summary": ["Found 1 high severity issue."],
        "structured": {"rows": []}
    }
    return task, result

def test_sarif_output_parity(sample_scan_data):
    """Proves SARIF output maintains exact structural parity post-refactor."""
    task, result = sample_scan_data
    sarif_str = reporting.generate_sarif_report(task, result)
    sarif_data = json.loads(sarif_str)

    # Assert base schema and tool data parity
    assert sarif_data["version"] == "2.1.0"
    assert sarif_data["runs"][0]["tool"]["driver"]["name"] == "TestScanner"

    # Assert rule extraction parity from the new _extract_sarif_rule_id helper
    rules = sarif_data["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1
    assert rules[0]["id"] == "cve-2024-0001"
    assert rules[0]["name"] == "Reflected Cross-Site Scripting"

    # Assert result mapping and location parity from the new _extract_sarif_locations helper
    results = sarif_data["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "cve-2024-0001"
    assert results[0]["level"] == "error"
    assert results[0]["message"]["text"] == "User input is reflected without sanitization."
    assert results[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "https://example.com/search"

def test_html_web_output_parity(sample_scan_data):
    """Proves Web HTML output correctly injects modularized markup from _build_web_finding_markup."""
    task, result = sample_scan_data
    html_str = reporting.generate_html_report(task, result)

    # Assert the modularized finding block rendered correctly with all data
    assert "Reflected Cross-Site Scripting" in html_str
    assert "severity-high" in html_str
    assert "User input is reflected without sanitization." in html_str
    assert "<pre>&lt;script&gt;alert(1)&lt;/script&gt;</pre>" in html_str  # Checks HTML escaping parity
    assert "Escape all user-supplied input." in html_str
    assert "CVE-2024-0001" in html_str

def test_html_pdf_output_parity(sample_scan_data):
    """Proves PDF HTML output correctly injects modularized markup from _build_pdf_finding_markup."""
    task, result = sample_scan_data

    # Test the internal HTML generator for the PDF to verify string parity
    pdf_html_str = reporting._generate_pdf_html_report(task, result)

    # Assert table-based PDF markup rendered correctly
    assert "<table class=\"finding-header\">" in pdf_html_str
    assert "Reflected Cross-Site Scripting" in pdf_html_str
    assert "User input is reflected without sanitization." in pdf_html_str
