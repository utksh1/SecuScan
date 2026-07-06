from backend.secuscan.reporting import ReportGenerator
import pytest


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


def test_generate_pdf_report_closes_buffer_on_pisa_error(monkeypatch):
    """Buffer must be closed even when pisa reports a render error."""
    import io as _io

    closed_buffers = []
    real_BytesIO = _io.BytesIO

    class TrackingBytesIO(real_BytesIO):
        def close(self):
            closed_buffers.append(True)
            super().close()

    monkeypatch.setattr(_io, "BytesIO", TrackingBytesIO)

    class FakePisaResult:
        err = True

    import xhtml2pdf.pisa as pisa_mod
    monkeypatch.setattr(pisa_mod, "CreatePDF", lambda **kw: FakePisaResult())

    with pytest.raises(RuntimeError, match="Failed to render"):
        ReportGenerator.generate_pdf_report(sample_task(), sample_result())

    assert closed_buffers, "BytesIO.close() was never called on render failure"


def test_generate_pdf_report_closes_buffer_on_unexpected_exception(monkeypatch):
    """Buffer must be closed and exception normalized to RuntimeError on crash."""
    import io as _io

    closed_buffers = []
    real_BytesIO = _io.BytesIO

    class TrackingBytesIO(real_BytesIO):
        def close(self):
            closed_buffers.append(True)
            super().close()

    monkeypatch.setattr(_io, "BytesIO", TrackingBytesIO)

    import xhtml2pdf.pisa as pisa_mod
    monkeypatch.setattr(pisa_mod, "CreatePDF", lambda **kw: (_ for _ in ()).throw(OSError("disk full")))

    with pytest.raises(RuntimeError, match="Failed to render"):
        ReportGenerator.generate_pdf_report(sample_task(), sample_result())

    assert closed_buffers, "BytesIO.close() was never called on unexpected exception"


def test_generate_pdf_report_chains_original_exception(monkeypatch):
    """The original cause must be preserved via exception chaining."""
    import xhtml2pdf.pisa as pisa_mod
    original = OSError("disk full")
    monkeypatch.setattr(pisa_mod, "CreatePDF", lambda **kw: (_ for _ in ()).throw(original))

    with pytest.raises(RuntimeError) as exc_info:
        ReportGenerator.generate_pdf_report(sample_task(), sample_result())

    assert exc_info.value.__cause__ is original


def test_generate_csv_report_closes_buffer_on_success(monkeypatch):
    """StringIO.close() must be called even on the happy path."""
    import io as _io

    closed_buffers = []
    real_StringIO = _io.StringIO

    class TrackingStringIO(real_StringIO):
        def close(self):
            closed_buffers.append(True)
            super().close()

    monkeypatch.setattr(_io, "StringIO", TrackingStringIO)

    result = ReportGenerator.generate_csv_report(sample_task(), sample_result())
    assert "Severity" in result
    assert closed_buffers, "StringIO.close() was never called on success"


def test_generate_csv_report_closes_buffer_on_failure(monkeypatch):
    """StringIO.close() must be called even when CSV writing fails."""
    import io as _io
    import csv as csv_mod

    closed_buffers = []
    real_StringIO = _io.StringIO

    class TrackingStringIO(real_StringIO):
        def close(self):
            closed_buffers.append(True)
            super().close()

    monkeypatch.setattr(_io, "StringIO", TrackingStringIO)
    monkeypatch.setattr(csv_mod, "writer", lambda f: (_ for _ in ()).throw(RuntimeError("bad writer")))

    with pytest.raises(RuntimeError):
        ReportGenerator.generate_csv_report(sample_task(), sample_result())

    assert closed_buffers, "StringIO.close() was never called on CSV failure"


def test_generate_pdf_report_raises_runtime_error_on_pisa_err(monkeypatch):
    """Route layer depends on RuntimeError; never a raw pisa-internal type."""
    import xhtml2pdf.pisa as pisa_mod

    class BadResult:
        err = 1  # truthy

    monkeypatch.setattr(pisa_mod, "CreatePDF", lambda **kw: BadResult())

    with pytest.raises(RuntimeError):
        ReportGenerator.generate_pdf_report(sample_task(), sample_result())
