from plugins.whois_lookup.parser import parse


def test_empty_output_returns_default_record():
    result = parse("")

    assert "findings" in result
    assert "rows" in result
    assert "detail" in result

    assert len(result["findings"]) == 1
    assert result["detail"]["registrar"] == "Unknown"


def test_rate_limited_output_returns_default_record():
    output = "WHOIS LIMIT EXCEEDED"

    result = parse(output)

    assert "findings" in result
    assert "rows" in result
    assert "detail" in result

    assert len(result["findings"]) == 1
    assert result["detail"]["registrar"] == "Unknown"
