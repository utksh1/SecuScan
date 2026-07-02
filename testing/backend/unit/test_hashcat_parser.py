from plugins.hashcat.parser import parse


def test_hashcat_parser_normal_output():
    output = """
    5f4dcc3b5aa765d61d8327deb882cf99:password123
    8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918:admin_pass
    """
    result = parse(output)

    assert result["count"] == 2
    assert len(result["findings"]) == 2
    assert len(result["recovered"]) == 2

    first_recovered = result["recovered"][0]
    assert first_recovered["hash"] == "5f4dcc3b5aa765d61d8327deb882cf99"
    assert first_recovered["password"] == "password123"

    first_finding = result["findings"][0]
    assert first_finding["title"] == "Hash Recovered"
    assert first_finding["category"] == "Password Recovery"
    assert first_finding["severity"] == "high"
    assert first_finding["metadata"]["hash"] == "5f4dcc3b5aa765d61d8327deb882cf99"
    assert first_finding["metadata"]["password"] == "password123"


def test_hashcat_parser_empty_and_whitespace():
    result = parse("")
    assert result["count"] == 0
    assert len(result["findings"]) == 0
    assert len(result["recovered"]) == 0

    result = parse("\n   \n\t\n")
    assert result["count"] == 0


def test_hashcat_parser_ignored_lines():
    # Lines starting with [ or missing colons or missing parts should be ignored
    output = """
    [status] hashcat running...
    [info] dictionary attack selected
    invalid_line_without_colon
    :emptyhash
    empty_password:
    :
    """
    result = parse(output)
    assert result["count"] == 0
    assert len(result["findings"]) == 0
    assert len(result["recovered"]) == 0


def test_hashcat_parser_mixed_output():
    output = """
    [status] running
    5f4dcc3b5aa765d61d8327deb882cf99:password123
    invalid_line
    8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918:admin_pass
    """
    result = parse(output)
    assert result["count"] == 2
    assert result["recovered"][0]["hash"] == "5f4dcc3b5aa765d61d8327deb882cf99"
    assert result["recovered"][1]["hash"] == "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
