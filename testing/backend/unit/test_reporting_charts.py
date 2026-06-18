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
            "depth": "deep"
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
                "description": "A SQL injection vulnerability exists in the login form.",
                "proof": "UNION SELECT username, password FROM users;",
                "remediation": "Use parameterized SQL queries and input sanitization.",
                "validated": True,
            },
            {
                "id": "finding-2",
                "title": "XSS Vulnerability",
                "category": "XSS",
                "severity": "HIGH",
                "target": "example.com/search.php",
                "description": "Reflected Cross-Site Scripting via query parameter.",
                "proof": "<script>alert(1)</script>",
                "remediation": "Escape user input in output HTML rendering.",
                "validated": False,
            }
        ],
        "structured": {
            "rows": []
        },
        "summary": ["Scan completed successfully."],
        "errors": []
    }

def test_generate_severity_chart():
    severity_counts = {
        "CRITICAL": 1,
        "HIGH": 2,
        "MEDIUM": 0,
        "LOW": 4,
        "INFO": 0
    }
    chart_data = ReportGenerator._generate_severity_chart(severity_counts)
    assert isinstance(chart_data, str)
    assert chart_data.startswith("data:image/png;base64,")

def test_html_report_contains_chart(sample_task, sample_result):
    html_report = ReportGenerator.generate_html_report(sample_task, sample_result)
    assert "Severity Distribution Chart" in html_report
    assert "data:image/png;base64," in html_report
