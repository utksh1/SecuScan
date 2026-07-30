from plugins.droopescan.parser import parse


def test_droopescan_severity_mapping():
    output = """
    {
      "vulnerabilities": [
        {"description": "Critical issue"}
      ],
      "interesting_urls": [
        {"description": "Exposed admin endpoint"}
      ],
      "themes": [
        {"description": "Theme detected"}
      ]
    }
    """

    result = parse(output)
    findings = result["findings"]

    severities = {f["title"]: f["severity"] for f in findings}

    assert severities["DroopeScan vulnerabilities"] == "high"
    assert severities["DroopeScan interesting_urls"] == "medium"
    assert severities["DroopeScan themes"] == "low"
