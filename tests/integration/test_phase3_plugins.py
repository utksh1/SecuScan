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
        
        # Start task
        response = test_client.post("/api/v1/task/start", json=payload)
        assert response.status_code == 200, f"Failed to start {plugin_id}: {response.text}"
        task_id = response.json()["task_id"]
        
        # Wait for completion
        max_retries = 10
        status = "unknown"
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

def test_phase3_plugins_discoverable(test_client):
    response = test_client.get("/api/v1/plugins")
    assert response.status_code == 200
    payload = response.json()
    plugin_ids = {plugin["id"] for plugin in payload["plugins"]}
    assert PHASE3_PLUGIN_IDS.issubset(plugin_ids)

def test_wpscan(test_client):
    mock_out = "Interesting Finding: /wp-login.php\n[!] XML-RPC is enabled"
    result = run_plugin_test(test_client, "wpscan", {"target": "http://wp.lab"}, mock_out)
    assert any("WordPress Finding" in f["title"] for f in result["structured"]["findings"])

def test_joomscan(test_client):
    mock_out = "[+] Vulnerable to: CVE-2015-8562\n[+] Joomla! version: 3.4.5"
    result = run_plugin_test(test_client, "joomscan", {"target": "http://joomla.lab"}, mock_out)
    assert any("Joomla! Vulnerability" in f["title"] for f in result["structured"]["findings"])

def test_droopescan(test_client):
    mock_out = "[+] Site is running Drupal 7\n[+] Interesting: /robots.txt"
    result = run_plugin_test(test_client, "droopescan", {"target": "http://drupal.lab"}, mock_out)
    assert any("CMS Discovery" in f["title"] for f in result["structured"]["findings"])

def test_yara_scan(test_client):
    mock_out = "my_rule /path/to/malicious_file\nanother_rule /path/to/another_file"
    result = run_plugin_test(test_client, "yara_scan", {"target": "/tmp", "rules": "/tmp/rules.yar"}, mock_out)
    assert any("YARA Match" in f["title"] for f in result["structured"]["findings"])

def test_volatility(test_client):
    mock_out = "Header1 Header2\nData1 Data2\nData3 Data4"
    result = run_plugin_test(test_client, "volatility", {"target": "mem.dump", "plugin_name": "pslist"}, mock_out)
    assert any("Volatility Artifact" in f["title"] for f in result["structured"]["findings"])

def test_hashcat(test_client):
    mock_out = "5f4dcc3b5aa765d61d8327deb882cf99:password\ne807f1fcf82d132f9bb018ca6738a19f:admin123"
    result = run_plugin_test(test_client, "hashcat", {"target": "hashes.txt", "hash_type": 0}, mock_out)
    assert any("Hash Recovered" in f["title"] for f in result["structured"]["findings"])

def test_metasploit(test_client):
    mock_out = "[*] Handler started\n[*] Found vulnerability: MS17-010"
    result = run_plugin_test(test_client, "metasploit", {"target": "10.0.0.1", "exploit": "eternalblue"}, mock_out)
    assert any("Metasploit Output" in f["title"] for f in result["structured"]["findings"])

def test_sqli_checker(test_client):
    mock_out = "Payload: ' OR 1=1 --\navailable databases [2]:\ndb1\ndb2"
    result = run_plugin_test(test_client, "sqli_checker", {"target": "http://api.lab/user?id=1"}, mock_out)
    assert any("SQL Injection Found" in f["title"] for f in result["structured"]["findings"])
    assert any("Databases Enumerated" in f["title"] for f in result["structured"]["findings"])
