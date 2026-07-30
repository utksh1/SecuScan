import json
import csv
import io
import pytest
from backend.secuscan.reporting import ReportGenerator

@pytest.fixture
def sample_task():
    return {
        "id": "task-123",
        "tool_name": "Test Scanner",
        "plugin_id": "test_plugin",
        "target": "example.com",
        "status": "completed",
        "created_at": "2026-06-17T12:00:00.000000Z",
        "preset": "Full Scan",
        "command_used": "test-scanner --target example.com",
        "inputs": {
            "depth": "deep",
            "threads": 4,
            "enable_ssl": True
        }
    }

@pytest.fixture
def sample_result():
    return {
        "findings": [
            {
                "id": "finding-1",
                "title": "SQL Injection",
                "category": "Injection",
                "severity": "CRITICAL",
                "target": "example.com/login.php",
                "cvss": 9.8,
                "cve": "CVE-2026-0001",
                "cwe": "CWE-89",
                "cpe": "cpe:/a:test:login:1.0",
                "validated": True,
                "validation_method": "Exploitation payload sent",
                "confidence_reason": "Vulnerability confirmed via active database response.",
                "description": "A SQL injection vulnerability exists in the login form.",
                "proof": "UNION SELECT username, password FROM users;",
                "remediation": "Use parameterized SQL queries and input sanitization.",
                "metadata": {
                    "payload": "' OR 1=1 --"
                }
            },
            {
                "id": "finding-2",
                "title": "XSS Vulnerability",
                "category": "XSS",
                "severity": "HIGH",
                "target": "example.com/search.php",
                "cvss": 7.5,
                "cve": "",
                "cwe": "CWE-79",
                "validated": False,
                "description": "Reflected Cross-Site Scripting via query parameter.",
                "proof": "<script>alert(1)</script>",
                "remediation": "Escape user input in output HTML rendering."
            }
        ],
        "structured": {
            "open_ports": [80, 443],
            "technologies": ["Apache", "PHP"],
            "rows": [
                {"port": 80, "service": "http"},
                {"port": 443, "service": "https"}
            ]
        },
        "summary": [
            "The scan completed successfully.",
            "Found two high-severity vulnerabilities."
        ],
        "errors": []
    }

def test_generate_csv_report(sample_task, sample_result):
    csv_report = ReportGenerator.generate_csv_report(sample_task, sample_result)
    assert isinstance(csv_report, str)

    # Read CSV
    f = io.StringIO(csv_report)
    reader = csv.reader(f)
    rows = list(reader)

    # Check headers
    assert len(rows) > 0
    headers = rows[0]
    expected_headers = [
        "Severity", "Title", "Category", "Target", "CVSS", "CVE", "CPE",
        "Validated", "Validation Method", "Confidence Reason", "Description",
        "Evidence", "Remediation"
    ]
    assert headers == expected_headers

    # Check rows
    assert len(rows) == 3  # Header + 2 findings
    assert rows[1][0] == "CRITICAL"
    assert rows[1][1] == "SQL Injection"
    assert rows[1][7] == "yes"
    assert rows[2][0] == "HIGH"
    assert rows[2][7] == "no"

def test_generate_html_report(sample_task, sample_result):
    html_report = ReportGenerator.generate_html_report(sample_task, sample_result)
    assert isinstance(html_report, str)
    assert "<!DOCTYPE html>" in html_report
    assert "SecuScan Report" in html_report
    assert "SQL Injection" in html_report
    assert "XSS Vulnerability" in html_report
    assert "example.com" in html_report

def test_generate_pdf_report(sample_task, sample_result):
    pdf_report = ReportGenerator.generate_pdf_report(sample_task, sample_result)
    assert isinstance(pdf_report, bytes)
    # PDF header signature
    assert pdf_report.startswith(b"%PDF")

def test_generate_sarif_report(sample_task, sample_result):
    sarif_report = ReportGenerator.generate_sarif_report(sample_task, sample_result)
    assert isinstance(sarif_report, str)

    # Parse JSON
    sarif_data = json.loads(sarif_report)
    assert sarif_data["version"] == "2.1.0"
    assert "runs" in sarif_data
    run = sarif_data["runs"][0]
    assert run["tool"]["driver"]["name"] == "Test Scanner"

    # Check results
    results = run["results"]
    assert len(results) == 2
    assert results[0]["ruleId"] == "cve-2026-0001"  # Derived from CVE
    assert results[0]["level"] == "error"
    assert results[1]["ruleId"] == "cwe-79"  # Derived from CWE
