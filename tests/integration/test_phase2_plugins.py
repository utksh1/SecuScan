import time
import re
from pathlib import Path
from unittest.mock import patch
from backend.secuscan.models import TaskStatus

PHASE2_PLUGIN_IDS = {
    "subdomain_discovery",
    "secret_scanner",
    "code_analyzer",
    "scapy_recon",
    "ssh_runner",
    "whois_lookup",
    "dns_enum",
}
SCANTOOLS_FILE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "data" / "scanTools.ts"


def parse_scantool_ids() -> set[str]:
    content = SCANTOOLS_FILE.read_text(encoding="utf-8")
    start = content.index("export const scanTools")
    end = content.index("export function getToolsByCategory")
    section = content[start:end]
    return set(re.findall(r"id:\\s*'([a-z0-9_-]+)'", section))


def run_plugin_test(test_client, plugin_id, inputs, mock_output):
    """Helper to run a plugin test with mocked execution."""
    with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
        mock_exec.return_value = (mock_output, 0)
        
        payload = {
            "plugin_id": plugin_id,
            "inputs": inputs,
            "consent_granted": True,
        }
        
        # Start task
        response = test_client.post("/api/v1/task/start", json=payload)
        assert response.status_code == 200, f"Failed to start {plugin_id}: {response.text}"
        task_id = response.json()["task_id"]
        
        # Wait for completion (since it's mocked, it should be fast)
        # In the test environment, the executor might be running in the same thread or very fast
        max_retries = 10
        for _ in range(max_retries):
            status_response = test_client.get(f"/api/v1/task/{task_id}/status")
            status = status_response.json()["status"]
            if status == TaskStatus.COMPLETED.value:
                break
            time.sleep(0.1)
        
        assert status == TaskStatus.COMPLETED.value, f"Task {task_id} did not complete for {plugin_id}"
        
        # Check result
        result_response = test_client.get(f"/api/v1/task/{task_id}/result")
        assert result_response.status_code == 200
        return result_response.json()


def test_phase2_plugins_discoverable_and_schema_accessible(test_client):
    response = test_client.get("/api/v1/plugins")
    assert response.status_code == 200
    payload = response.json()

    plugin_ids = {plugin["id"] for plugin in payload["plugins"]}
    assert PHASE2_PLUGIN_IDS.issubset(plugin_ids)

    for plugin in payload["plugins"]:
        assert "requires_consent" in plugin
        assert "availability" in plugin
        assert "missing_binaries" in plugin["availability"]
        assert "runnable" in plugin["availability"]

    for plugin_id in PHASE2_PLUGIN_IDS:
        schema = test_client.get(f"/api/v1/plugin/{plugin_id}/schema")
        assert schema.status_code == 200


def test_all_scantools_have_backend_plugins(test_client):
    response = test_client.get("/api/v1/plugins")
    assert response.status_code == 200
    backend_plugin_ids = {plugin["id"] for plugin in response.json()["plugins"]}
    scan_tool_ids = parse_scantool_ids()
    assert scan_tool_ids.issubset(backend_plugin_ids), (
        f"Missing backend plugins for scanTools: {sorted(scan_tool_ids - backend_plugin_ids)}"
    )

def test_subdomain_discovery(test_client):
    mock_out = "admin.example.com\ndev.example.com\napi.example.com"
    result = run_plugin_test(test_client, "subdomain_discovery", {"target": "example.com"}, mock_out)
    assert len(result["structured"]["findings"]) > 0
    assert "admin.example.com" in result["raw_output_excerpt"]

def test_secret_scanner(test_client):
    import json
    mock_out = json.dumps([{
        "RuleID": "generic-api-key",
        "File": "config.py",
        "StartLine": 10,
        "Offender": "SG.xxxx"
    }])
    result = run_plugin_test(test_client, "secret_scanner", {"target": "/tmp"}, mock_out)
    assert any("Secret Leak" in f["title"] for f in result["structured"]["findings"])

def test_code_analyzer(test_client):
    import json
    mock_out = json.dumps({
        "results": [{
            "issue_text": "Use of assert detected.",
            "filename": "main.py",
            "line_number": 10,
            "issue_severity": "low",
            "issue_confidence": "high",
            "test_id": "B101"
        }]
    })
    result = run_plugin_test(test_client, "code_analyzer", {"target": "/tmp"}, mock_out)
    assert any("B101" == f["metadata"]["test_id"] for f in result["structured"]["findings"])

def test_scapy_recon(test_client):
    mock_out = "UP: 192.168.1.5 - 00:11:22:33:44:55\nUP: 192.168.1.1"
    result = run_plugin_test(test_client, "scapy_recon", {"target": "192.168.1.0/24"}, mock_out)
    assert any("Live Host Discovered" in f["title"] for f in result["structured"]["findings"])

def test_ssh_runner(test_client):
    mock_out = " 11:45:01 up 10 days,  2:34,  1 user,  load average: 0.00, 0.01, 0.05"
    result = run_plugin_test(
        test_client,
        "ssh_runner",
        {"target": "10.0.0.1", "username": "root", "command": "uptime"},
        mock_out,
    )
    assert "load average" in result["raw_output_excerpt"]

def test_whois_lookup(test_client):
    mock_out = "Registrar: SafeNames Ltd.\nRegistry Expiry Date: 2026-01-01\nName Server: NS1.EXAMPLE.COM"
    result = run_plugin_test(test_client, "whois_lookup", {"target": "example.com"}, mock_out)
    assert result["structured"]["detail"]["registrar"] == "SafeNames Ltd."

def test_dns_enum(test_client):
    mock_out = "[*] A example.com 93.184.216.34\n[*] MX mail.example.com 10"
    result = run_plugin_test(test_client, "dns_enum", {"target": "example.com"}, mock_out)
    assert result["structured"]["count"] >= 2
    assert any(r["type"] == "MX" for r in result["structured"]["records"])
