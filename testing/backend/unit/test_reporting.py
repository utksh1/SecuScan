from backend.secuscan.reporting import ReportGenerator


def sample_task():
    return {
        "id": "task-123",
        "tool_name": "http_inspector",
        "plugin_id": "http_inspector",
        "target": "https://example.com",
        "status": "completed",
        "created_at": "2026-05-14T10:30:00",
        "preset": "standard",
        "inputs_json": "{\"target\": \"https://example.com\", \"display_options\": \"EPV\", \"safe_mode\": true}",
        "command_used": "nikto -h https://example.com -Display EPV -Format json -output -",
    }


def sample_result():
    return {
        "structured": {
            "findings": [
                {
                    "title": "Exposed admin panel",
                    "category": "Exposure",
                    "severity": "high",
                    "target": "https://example.com/admin",
                    "description": "Admin panel is reachable without network restrictions.",
                    "remediation": "Restrict access with authentication and IP controls.",
                    "proof": "HTTP 200 returned for /admin",
                    "cve": "CVE-2026-0001",
                    "cvss": 8.1,
                }
            ],
            "rows": [{"path": "/admin", "status": 200}],
            "open_ports": [80, 443],
        }
    }


def test_generate_html_report_uses_nested_structured_findings():
    html = ReportGenerator.generate_html_report(sample_task(), sample_result())

    assert "Exposed admin panel" in html
    assert "HTTP 200 returned for /admin" in html
    assert "Restrict access with authentication and IP controls." in html
    assert "Structured rows" in html
    assert "Scan Parameters" in html
    assert "Display Options" in html
    assert "Preset" in html
    assert "data:image/png;base64" in html


def test_generate_pdf_report_returns_pdf_bytes_for_nested_structured_findings():
    pdf_bytes = ReportGenerator.generate_pdf_report(sample_task(), sample_result())

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_generate_pdf_report_handles_long_wrapping_content():
    task = {
        **sample_task(),
        "target": "https://example.com/really/long/path/that/should/wrap/instead/of/overlapping/with/the/header/or/metadata",
    }
    result = sample_result()
    finding = result["structured"]["findings"][0]
    finding["title"] = "Long finding title that should wrap cleanly without colliding with the severity badge"
    finding["description"] = " ".join(["This description should wrap through several lines."] * 35)
    finding["proof"] = "\n".join([f"evidence-line-{index}: HTTP 200 with unexpected exposure" for index in range(40)])
    finding["remediation"] = " ".join(["Apply layered access controls and verify the exposed surface again."] * 20)

    pdf_bytes = ReportGenerator.generate_pdf_report(task, result)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 2000


def test_generate_csv_report_includes_new_columns():
    csv_output = ReportGenerator.generate_csv_report(sample_task(), sample_result())

    assert (
        "Severity,Title,Category,Target,CVSS,CVE,CPE,Validated,Validation Method,"
        "Confidence Reason,Description,Evidence,Remediation"
    ) in csv_output
    assert "Exposed admin panel" in csv_output
    assert "CVE-2026-0001" in csv_output


def test_build_report_payload_includes_parameters_and_command():
    payload = ReportGenerator._build_report_payload(sample_task(), sample_result())

    labels = {item["label"] for item in payload["scan_parameters"]}
    assert {"Target", "Plugin", "Preset", "Display Options", "Safe Mode", "Command"} <= labels
    assert payload["command_used"].startswith("nikto -h")
