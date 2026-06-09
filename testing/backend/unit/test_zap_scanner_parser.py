import json

from plugins.zap_scanner.parser import parse


ZAP_ALERTS = [
    {
        "title": "SQL Injection",
        "severity": "high",
        "description": "SQL injection may be possible via the 'id' parameter.",
        "remediation": "Use parameterized queries.",
        "metadata": {
            "url": "https://example.com/page?id=1",
            "param": "id",
            "cweid": "89",
        },
    },
    {
        "title": "XSS Vulnerability",
        "severity": "medium",
        "description": "Reflected XSS detected in the 'q' parameter.",
        "remediation": "Encode output and validate input.",
        "metadata": {
            "url": "https://example.com/search?q=<script>",
            "param": "q",
            "cweid": "79",
        },
    },
    {
        "title": "Missing Security Header",
        "severity": "low",
        "description": "X-Content-Type-Options header is not set.",
        "remediation": "Add the X-Content-Type-Options: nosniff header.",
        "metadata": {
            "url": "https://example.com/",
            "param": "",
            "cweid": "693",
        },
    },
    {
        "title": "Informational Cookie",
        "severity": "info",
        "description": "Cookie without Secure flag.",
        "remediation": "Review cookie configuration.",
        "metadata": {
            "url": "https://example.com/session",
            "param": "sessionid",
            "cweid": "614",
        },
    },
]


def _payload(findings, count=None):
    if count is None:
        count = len(findings)
    return json.dumps({"findings": findings, "count": count, "items": findings})


def test_parse_with_valid_zap_json():
    result = parse(_payload(ZAP_ALERTS))

    assert result["count"] == 4
    assert len(result["findings"]) == 4
    assert result["findings"][0]["title"] == "SQL Injection"
    assert result["findings"][0]["severity"] == "high"
    assert result["findings"][0]["category"] == "DAST"
    assert result["findings"][0]["metadata"]["cweid"] == "89"
    assert result["findings"][1]["title"] == "XSS Vulnerability"
    assert result["findings"][1]["severity"] == "medium"
    assert result["findings"][2]["title"] == "Missing Security Header"
    assert result["findings"][2]["severity"] == "low"
    assert result["findings"][3]["title"] == "Informational Cookie"
    assert result["findings"][3]["severity"] == "info"


def test_parse_with_empty_findings():
    result = parse(json.dumps({"findings": [], "count": 0, "items": []}))
    assert result["count"] == 0
    assert result["findings"] == []


def test_parse_with_invalid_json():
    result = parse("not json at all")
    assert result["count"] == 0
    assert result["findings"] == []


def test_parse_falls_back_to_items_key():
    result = parse(json.dumps({"items": ZAP_ALERTS[:2]}))
    assert result["count"] == 2
    assert result["findings"][0]["title"] == "SQL Injection"


def test_parse_handles_missing_severity_gracefully():
    alert = {"title": "Observation", "description": "Something noticed"}
    result = parse(json.dumps({"findings": [alert]}))
    assert result["count"] == 1
    assert result["findings"][0]["severity"] == "info"


def test_parse_skips_non_dict_items():
    payload = json.dumps({"findings": [{"title": "Valid"}, "not a dict", None, 42]})
    result = parse(payload)
    assert result["count"] == 1
    assert result["findings"][0]["title"] == "Valid"
