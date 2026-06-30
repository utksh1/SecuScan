from plugins.httpx.parser import parse


def test_httpx_parser_normal_output():
    # Mix of normal lines and lines with keywords triggering "low" severity
    output = (
        "https://example.com [200] [status_code]\n"
        "https://vuln-sub.example.com [200] vulnerable to CVE-2023-XXXX\n"
        "https://exposed.example.com [200] config exposed\n"
        "https://alive.example.com [200]\n"
        "https://another.example.com found\n"
        "https://test.example.com detected\n"
        "https://open-port.example.com open\n"
    )

    result = parse(output)

    assert result["count"] == 7
    assert len(result["findings"]) == 7
    assert len(result["items"]) == 7

    # Verify findings structure
    for finding in result["findings"]:
        assert finding["title"] == "httpx Observation"
        assert finding["category"] == "Recon"
        assert "remediation" in finding
        assert "metadata" in finding
        assert "raw_line" in finding["metadata"]

    # Verify severity logic
    # "https://example.com [200] [status_code]" -> info
    assert result["findings"][0]["severity"] == "info"
    assert result["findings"][0]["description"] == "https://example.com [200] [status_code]"

    # "https://vuln-sub.example.com [200] vulnerable to CVE-2023-XXXX" -> low (vulnerable)
    assert result["findings"][1]["severity"] == "low"

    # "https://exposed.example.com [200] config exposed" -> low (exposed)
    assert result["findings"][2]["severity"] == "low"

    # "https://alive.example.com [200]" -> info (contains no severity keyword; wait, does "https://alive.example.com" trigger "alive"?
    # Yes, "alive" is in "https://alive.example.com" because of the domain name!)
    # Let's verify: normalized = "https://alive.example.com [200]". "alive" in normalized is True. So it's low.
    assert result["findings"][3]["severity"] == "low"

    # "https://another.example.com found" -> low (found)
    assert result["findings"][4]["severity"] == "low"

    # "https://test.example.com detected" -> low (detected)
    assert result["findings"][5]["severity"] == "low"

    # "https://open-port.example.com open" -> low (open)
    assert result["findings"][6]["severity"] == "low"


def test_httpx_parser_empty_output():
    # Empty string
    result = parse("")
    assert result["count"] == 0
    assert result["findings"] == []
    assert result["items"] == []

    # Whitespace-only string
    result = parse("   \n\n   \n")
    assert result["count"] == 0
    assert result["findings"] == []
    assert result["items"] == []


def test_httpx_parser_malformed_output():
    # Malformed output with non-ASCII or special/binary characters
    output = "https://example.com \x00\x01\x02\n\n\n★☆★\n"
    result = parse(output)

    assert result["count"] == 2
    assert len(result["findings"]) == 2
    assert result["findings"][0]["description"] == "https://example.com \x00\x01\x02"
    assert result["findings"][1]["description"] == "★☆★"
    assert result["findings"][0]["severity"] == "info"
    assert result["findings"][1]["severity"] == "info"


def test_httpx_parser_truncation_limit():
    # Create 250 lines
    lines = [f"https://host{i}.example.com" for i in range(250)]
    output = "\n".join(lines)

    result = parse(output)

    # Parser should truncate to 200 lines
    assert result["count"] == 200
    assert len(result["findings"]) == 200
    assert len(result["items"]) == 200
    assert result["items"][0] == "https://host0.example.com"
    assert result["items"][-1] == "https://host199.example.com"
