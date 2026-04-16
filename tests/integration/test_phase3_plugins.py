import time
from unittest.mock import patch

from backend.secuscan.models import TaskStatus

PHASE3_PLUGIN_IDS = {
    "wpscan",
    "joomscan",
    "droopescan",
    "yara_scan",
    "volatility",
    "hashcat",
    "metasploit",
    "sqli_checker",
}


def run_plugin_test(test_client, plugin_id, inputs, mock_output):
    """Helper to run a plugin test with mocked execution."""
    with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
        mock_exec.return_value = (mock_output, 0)

        payload = {
            "plugin_id": plugin_id,
            "inputs": inputs,
            "consent_granted": True,
        }

        response = test_client.post("/api/v1/task/start", json=payload)
        assert response.status_code == 200, f"Failed to start {plugin_id}: {response.text}"
        task_id = response.json()["task_id"]

        max_retries = 10
        status = "unknown"
        for _ in range(max_retries):
            status_response = test_client.get(f"/api/v1/task/{task_id}/status")
            status = status_response.json()["status"]
            if status == TaskStatus.COMPLETED.value:
                break
            time.sleep(0.1)

        assert status == TaskStatus.COMPLETED.value, f"Task {task_id} did not complete for {plugin_id}"

        result_response = test_client.get(f"/api/v1/task/{task_id}/result")
        assert result_response.status_code == 200
        return result_response.json()


def test_phase3_plugins_discoverable_and_schema_accessible(test_client):
    response = test_client.get("/api/v1/plugins")
    assert response.status_code == 200
    payload = response.json()

    plugin_ids = {plugin["id"] for plugin in payload["plugins"]}
    assert PHASE3_PLUGIN_IDS.issubset(plugin_ids)

    for plugin in payload["plugins"]:
        assert "requires_consent" in plugin
        assert "availability" in plugin
        assert "runnable" in plugin["availability"]
        assert "missing_binaries" in plugin["availability"]

    for plugin_id in PHASE3_PLUGIN_IDS:
        schema = test_client.get(f"/api/v1/plugin/{plugin_id}/schema")
        assert schema.status_code == 200


def test_wpscan(test_client):
    mock_out = '{"plugins":{"sample-plugin":{"vulnerabilities":[{"title":"CVE-2026-1000"}]}}}'
    result = run_plugin_test(
        test_client,
        "wpscan",
        {"target": "https://wp.lab", "enumerate": "vp"},
        mock_out,
    )
    assert any("WordPress Plugin Vulnerability" in f["title"] for f in result["structured"]["findings"])


def test_joomscan(test_client):
    mock_out = "[+] Vulnerable to: CVE-2015-8562\n[+] Joomla! version: 3.4.5"
    result = run_plugin_test(test_client, "joomscan", {"target": "https://joomla.lab"}, mock_out)
    assert any("Joomla Vulnerability" in f["title"] for f in result["structured"]["findings"])


def test_droopescan(test_client):
    mock_out = '{"vulnerabilities":[{"description":"CVE-2025-0001"}],"interesting urls":[{"description":"/admin"}]}'
    result = run_plugin_test(test_client, "droopescan", {"target": "https://drupal.lab"}, mock_out)
    assert any("DroopeScan vulnerabilities" in f["title"] for f in result["structured"]["findings"])


def test_yara_scan(test_client):
    mock_out = "mal_rule /tmp/malicious.bin\nbackdoor_rule /tmp/agent.bin"
    result = run_plugin_test(
        test_client,
        "yara_scan",
        {"target": "/tmp", "rules": "/tmp/rules.yar"},
        mock_out,
    )
    assert any("YARA Match" in f["title"] for f in result["structured"]["findings"])


def test_volatility(test_client):
    mock_out = "Offset Name PID\n0x1 explorer.exe 1234\n0x2 lsass.exe 456"
    result = run_plugin_test(
        test_client,
        "volatility",
        {"target": "/tmp/mem.dump", "plugin_name": "windows.pslist.PsList"},
        mock_out,
    )
    assert any("Volatility Artifact" in f["title"] for f in result["structured"]["findings"])


def test_hashcat(test_client):
    mock_out = "5f4dcc3b5aa765d61d8327deb882cf99:password"
    result = run_plugin_test(
        test_client,
        "hashcat",
        {"target": "/tmp/hashes.txt", "hash_type": 0, "attack_mode": 0, "wordlist": "/tmp/words.txt"},
        mock_out,
    )
    assert any("Hash Recovered" in f["title"] for f in result["structured"]["findings"])


def test_metasploit(test_client):
    mock_out = "[*] Handler started\n[*] Meterpreter session 2 opened"
    result = run_plugin_test(
        test_client,
        "metasploit",
        {
            "target": "10.0.0.10",
            "module": "exploit/multi/handler",
            "payload": "generic/shell_reverse_tcp",
        },
        mock_out,
    )
    assert any("Metasploit Session Opened" in f["title"] for f in result["structured"]["findings"])


def test_sqli_checker(test_client):
    mock_out = "Payload: ' OR 1=1 --\navailable databases [2]:\nmain\naudit"
    result = run_plugin_test(
        test_client,
        "sqli_checker",
        {"target": "https://api.lab/user?id=1", "level": 1, "risk": 1, "technique": "BEUSTQ"},
        mock_out,
    )
    findings = result["structured"]["findings"]
    assert any("SQL Injection Found" in f["title"] for f in findings)
    assert any("Databases Enumerated" in f["title"] for f in findings)
