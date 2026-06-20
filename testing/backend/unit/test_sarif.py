import json
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
        "inputs_json": '{"target": "https://example.com", "display_options": "EPV", "safe_mode": true}',
        "command_used": "nikto -h https://example.com -Display EPV -Format json -output -",
    }


def test_generate_sarif_report_with_typical_findings():
    result = {
        "structured": {
            "findings": [
                {
                    "title": "Exposed admin panel",
                    "category": "Exposure",
                    "severity": "HIGH",
                    "target": "src/admin.py:45",
                    "description": "Admin panel is reachable without restrictions.",
                    "remediation": "Restrict access.",
                    "cve": "CVE-2026-0001",
                    "cvss": 8.1,
                    "cpe": "cpe:/a:nginx:nginx:1.18.0",
                    "validated": True,
                    "validation_method": "service_fingerprint",
                    "confidence_reason": "Matched live service banner and correlated local CPE intelligence.",
                },
                {
                    "title": "Cross-Site Scripting",
                    "category": "XSS Injection",
                    "severity": "MEDIUM",
                    "target": "http://example.com:8080/search?q=xss",
                    "description": "Reflected XSS found.",
                    "remediation": "Escape input.",
                    "cwe": "CWE-79",
                },
                {
                    "title": "Information Disclosure",
                    "category": "Info Leak",
                    "severity": "INFO",
                    "target": "src/config.py",
                    "description": "Version leaked in header.",
                    "remediation": "Hide version.",
                    "id": "leak-101",
                },
            ]
        }
    }

    sarif_str = ReportGenerator.generate_sarif_report(sample_task(), result)
    sarif = json.loads(sarif_str)

    # Assert version and schema
    assert sarif["version"] == "2.1.0"
    assert (
        sarif["$schema"]
        == "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json"
    )

    # Assert tool driver
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "http_inspector"
    assert run["tool"]["driver"]["version"] == "1.0.0"

    # Assert rules
    rules = run["tool"]["driver"]["rules"]
    assert len(rules) == 3

    # Rule 0 (CVE)
    assert rules[0]["id"] == "cve-2026-0001"
    assert rules[0]["name"] == "Exposed admin panel"
    assert rules[0]["shortDescription"]["text"] == "Exposed admin panel"
    assert (
        rules[0]["fullDescription"]["text"]
        == "Admin panel is reachable without restrictions."
    )
    assert rules[0]["help"]["text"] == "Restrict access."
    assert rules[0]["properties"]["cpe"] == "cpe:/a:nginx:nginx:1.18.0"
    assert rules[0]["properties"]["validated"] is True

    # Rule 1 (CWE)
    assert rules[1]["id"] == "cwe-79"
    assert rules[1]["name"] == "Cross-Site Scripting"

    # Rule 2 (ID)
    assert rules[2]["id"] == "leak-101"
    assert rules[2]["name"] == "Information Disclosure"

    # Assert results
    results = run["results"]
    assert len(results) == 3

    # Result 0 (File with line)
    assert results[0]["ruleId"] == "cve-2026-0001"
    assert results[0]["level"] == "error"  # HIGH -> error
    assert results[0]["properties"]["cpe"] == "cpe:/a:nginx:nginx:1.18.0"
    assert results[0]["properties"]["validated"] is True
    loc0 = results[0]["locations"][0]["physicalLocation"]
    assert loc0["artifactLocation"]["uri"] == "src/admin.py"
    assert loc0["region"]["startLine"] == 45

    # Result 1 (URL - should NOT extract port 8080 as line number)
    assert results[1]["ruleId"] == "cwe-79"
    assert results[1]["level"] == "warning"  # MEDIUM -> warning
    loc1 = results[1]["locations"][0]["physicalLocation"]
    assert loc1["artifactLocation"]["uri"] == "http://example.com:8080/search?q=xss"
    assert "region" not in loc1  # Port 8080 must not be treated as a line number

    # Result 2 (File without line)
    assert results[2]["ruleId"] == "leak-101"
    assert results[2]["level"] == "note"  # INFO -> note
    loc2 = results[2]["locations"][0]["physicalLocation"]
    assert loc2["artifactLocation"]["uri"] == "src/config.py"
    assert "region" not in loc2


def test_generate_sarif_report_with_empty_findings():
    result = {"structured": {"findings": []}}

    sarif_str = ReportGenerator.generate_sarif_report(sample_task(), result)
    sarif = json.loads(sarif_str)

    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "http_inspector"
    assert len(run["tool"]["driver"]["rules"]) == 0
    assert len(run["results"]) == 0
