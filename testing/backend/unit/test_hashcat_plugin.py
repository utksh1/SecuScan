"""
Unit tests for plugins/hashcat/parser.py.
"""

import pytest
from pathlib import Path

from plugins.hashcat.parser import parse


class TestParseHashcatOutput:
    def test_parses_single_hash_credential(self):
        output = "5f4dcc3b5aa765d61d8327deb882cf99:password123"
        result = parse(output)
        assert result["count"] == 1
        assert len(result["findings"]) == 1

    def test_parses_multiple_hash_credentials(self):
        output = (
            "hash1:password1\n"
            "hash2:password2\n"
            "hash3:password3\n"
        )
        result = parse(output)
        assert result["count"] == 3
        assert len(result["findings"]) == 3

    def test_finding_has_high_severity(self):
        output = "abc123:secretpass"
        result = parse(output)
        assert result["findings"][0]["severity"] == "high"

    def test_finding_has_correct_category(self):
        output = "hash1:pass1"
        result = parse(output)
        assert result["findings"][0]["category"] == "Password Recovery"

    def test_finding_title_is_hash_recovered(self):
        output = "hash1:pass1"
        result = parse(output)
        assert result["findings"][0]["title"] == "Hash Recovered"

    def test_metadata_contains_hash_and_password(self):
        output = "deadbeef:testpass"
        result = parse(output)
        meta = result["findings"][0]["metadata"]
        assert meta["hash"] == "deadbeef"
        assert meta["password"] == "testpass"

    def test_recovered_list_contains_hash_and_password(self):
        output = "cafebabe:supersecret"
        result = parse(output)
        assert len(result["recovered"]) == 1
        assert result["recovered"][0]["hash"] == "cafebabe"
        assert result["recovered"][0]["password"] == "supersecret"

    def test_skips_empty_lines(self):
        output = "hash1:pass1\n\n\nhash2:pass2"
        result = parse(output)
        assert result["count"] == 2

    def test_skips_lines_starting_with_bracket(self):
        output = "[foo]\nhash1:pass1\n[bar]\nhash2:pass2"
        result = parse(output)
        assert result["count"] == 2

    def test_skips_lines_without_colon(self):
        output = "hash_without_colon\nhash1:pass1"
        result = parse(output)
        assert result["count"] == 1

    def test_skips_empty_hash(self):
        output = ":password1\nhash2:pass2"
        result = parse(output)
        assert result["count"] == 1
        assert result["findings"][0]["metadata"]["hash"] == "hash2"

    def test_skips_empty_password(self):
        output = "hash1:\nhash2:pass2"
        result = parse(output)
        assert result["count"] == 1
        assert result["findings"][0]["metadata"]["hash"] == "hash2"

    def test_strips_whitespace_from_hash_and_password(self):
        output = "  hash123  :  mypassword  "
        result = parse(output)
        assert result["findings"][0]["metadata"]["hash"] == "hash123"
        assert result["findings"][0]["metadata"]["password"] == "mypassword"

    def test_empty_input_returns_empty_findings(self):
        result = parse("")
        assert result["count"] == 0
        assert result["findings"] == []
        assert result["recovered"] == []

    def test_whitespace_only_input_returns_empty_findings(self):
        result = parse("   \n  \n   ")
        assert result["count"] == 0
        assert result["findings"] == []

    def test_count_reflects_number_of_cracked_hashes(self):
        output = "\n".join(f"hash{i}:pass{i}" for i in range(5))
        result = parse(output)
        assert result["count"] == 5

    def test_finding_description_contains_hash(self):
        output = "a1b2c3d4e5f6:mypassword"
        result = parse(output)
        desc = result["findings"][0]["description"]
        assert "a1b2c3d4e5f6" in desc

    def test_remediation_present(self):
        output = "hash1:pass1"
        result = parse(output)
        assert "remediation" in result["findings"][0]
        assert len(result["findings"][0]["remediation"]) > 0
