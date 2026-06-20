import json
import sqlite3

from backend.secuscan.config import settings


def _seed_task(
    task_id: str, tool: str, target: str, created_at: str, status: str = "completed"
):
    conn = sqlite3.connect(settings.database_path)
    conn.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, status, created_at, preset, inputs_json, command_used, structured_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            tool,
            tool,
            target,
            status,
            created_at,
            "standard",
            json.dumps({"target": target}),
            f"{tool} {target}",
            json.dumps({"findings": []}),
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def test_csv_filename_url_target(test_client):
    task_id = "fn-csv-url-001"
    _seed_task(task_id, "http_inspector", "https://example.com", "2026-04-10T12:00:00")

    response = test_client.get(f"/api/v1/task/{task_id}/report/csv")
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert "attachment" in cd
    assert "secuscan_http-inspector_example-com_2026-04-10.csv" in cd


def test_csv_filename_hostport_target(test_client):
    task_id = "fn-csv-hp-001"
    _seed_task(task_id, "port_scanner", "192.168.1.1:8080", "2026-03-05T08:00:00")

    response = test_client.get(f"/api/v1/task/{task_id}/report/csv")
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert "secuscan_port-scanner_192-168-1-1-8080_2026-03-05.csv" in cd


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------


def test_html_filename_url_target(test_client):
    task_id = "fn-html-url-001"
    _seed_task(task_id, "nikto", "http://testsite.local", "2026-02-20T09:30:00")

    response = test_client.get(f"/api/v1/task/{task_id}/report/html")
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert "secuscan_nikto_testsite-local_2026-02-20.html" in cd


def test_html_filename_hostport_target(test_client):
    task_id = "fn-html-hp-001"
    _seed_task(task_id, "recon_scanner", "10.0.0.5:443", "2026-01-15T14:00:00")

    response = test_client.get(f"/api/v1/task/{task_id}/report/html")
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert "secuscan_recon-scanner_10-0-0-5-443_2026-01-15.html" in cd


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def test_pdf_filename_url_target(test_client):
    task_id = "fn-pdf-url-001"
    _seed_task(
        task_id, "http_inspector", "https://target.example.org", "2026-05-01T00:00:00"
    )

    response = test_client.get(f"/api/v1/task/{task_id}/report/pdf")
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert "secuscan_http-inspector_target-example-org_2026-05-01.pdf" in cd


def test_pdf_filename_hostport_target(test_client):
    task_id = "fn-pdf-hp-001"
    _seed_task(task_id, "port_scanner", "172.16.0.1:22", "2026-04-22T18:00:00")

    response = test_client.get(f"/api/v1/task/{task_id}/report/pdf")
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert "secuscan_port-scanner_172-16-0-1-22_2026-04-22.pdf" in cd


# ---------------------------------------------------------------------------
# SARIF
# ---------------------------------------------------------------------------


def test_sarif_filename_url_target(test_client):
    task_id = "fn-sarif-url-001"
    _seed_task(
        task_id, "http_inspector", "https://scan.example.com", "2026-05-10T10:00:00"
    )

    response = test_client.get(f"/api/v1/task/{task_id}/report/sarif")
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert "secuscan_http-inspector_scan-example-com_2026-05-10.sarif" in cd


def test_sarif_filename_hostport_target(test_client):
    task_id = "fn-sarif-hp-001"
    _seed_task(task_id, "recon_scanner", "203.0.113.5:80", "2026-05-11T11:00:00")

    response = test_client.get(f"/api/v1/task/{task_id}/report/sarif")
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert "secuscan_recon-scanner_203-0-113-5-80_2026-05-11.sarif" in cd


# ---------------------------------------------------------------------------
# Error paths — 404 and unfinished task do not produce download headers
# ---------------------------------------------------------------------------


def test_report_404_for_missing_task(test_client):
    response = test_client.get("/api/v1/task/does-not-exist-xyz/report/csv")
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]


def test_report_400_for_unfinished_task(test_client):
    task_id = "fn-running-001"
    _seed_task(
        task_id,
        "http_inspector",
        "https://example.com",
        "2026-05-14T10:00:00",
        status="running",
    )

    for fmt in ("csv", "html", "pdf", "sarif"):
        response = test_client.get(f"/api/v1/task/{task_id}/report/{fmt}")
        assert response.status_code == 400
        assert "Task is not finished yet" in response.json()["detail"]
