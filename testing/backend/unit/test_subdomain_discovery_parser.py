"""Dedicated parser unit tests for plugins/subdomain_discovery (issue #1436).

Covers:
  - Normal output: one or more subdomains, one per line.
  - Single-subdomain output.
  - Output with blank lines / surrounding whitespace.
  - Empty string input.
  - Whitespace-only input.
  - Malformed / non-subdomain lines (parser must not crash).
  - Return-value contract: keys, types, and counts are always consistent.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings

PLUGIN_ID = "subdomain_discovery"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"


def _load_parser():
    """Dynamically load the plugin's parser.py module."""
    spec = importlib.util.spec_from_file_location("subdomain_discovery_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None, (
        f"Cannot load parser from {PARSER_PATH} - check plugins_dir setting"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def parser():
    """Module-scoped fixture so the file is loaded once for all tests."""
    return _load_parser()


def _assert_finding_shape(finding, expected_subdomain):
    """Assert that a single finding dict has the expected structure and values."""
    assert finding["title"] == f"Subdomain Discovered: {expected_subdomain}"
    assert finding["category"] == "Subdomain"
    assert finding["severity"] == "info"
    assert isinstance(finding["description"], str) and finding["description"]
    assert isinstance(finding["remediation"], str) and finding["remediation"]
    meta = finding["metadata"]
    assert meta["subdomain"] == expected_subdomain
    assert meta["source"] == "subfinder"
    assert meta["confidence"] == "high"
    assert expected_subdomain in meta["evidence"]


class TestParserWithFixtureSampleOutput:
    """Tests using the canonical sample_output.txt fixture."""

    def test_fixture_file_exists(self):
        assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"

    def test_returns_correct_count(self, parser):
        result = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert result["count"] == 3

    def test_returns_correct_subdomains_list(self, parser):
        result = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert result["subdomains"] == [
            "api.secuscan.in",
            "staging.secuscan.in",
            "dev.secuscan.in",
        ]

    def test_findings_length_matches_count(self, parser):
        result = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert len(result["findings"]) == result["count"]

    def test_first_finding_has_correct_shape(self, parser):
        result = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
        _assert_finding_shape(result["findings"][0], "api.secuscan.in")

    def test_all_findings_have_correct_shape(self, parser):
        result = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
        expected = ["api.secuscan.in", "staging.secuscan.in", "dev.secuscan.in"]
        for finding, subdomain in zip(result["findings"], expected):
            _assert_finding_shape(finding, subdomain)


class TestParserReturnContract:
    """Verify the return-value contract (keys and types) for all inputs."""

    def test_result_always_has_required_keys(self, parser):
        for raw in ["", "   ", "api.example.com\nsub.example.com"]:
            result = parser.parse(raw)
            assert "findings" in result
            assert "count" in result
            assert "subdomains" in result

    def test_findings_is_always_a_list(self, parser):
        for raw in ["", "api.example.com"]:
            assert isinstance(parser.parse(raw)["findings"], list)

    def test_subdomains_is_always_a_list(self, parser):
        for raw in ["", "api.example.com"]:
            assert isinstance(parser.parse(raw)["subdomains"], list)

    def test_count_equals_len_subdomains(self, parser):
        for raw in ["", "a.example.com", "a.example.com\nb.example.com"]:
            result = parser.parse(raw)
            assert result["count"] == len(result["subdomains"])

    def test_count_equals_len_findings(self, parser):
        for raw in ["", "a.example.com", "a.example.com\nb.example.com"]:
            result = parser.parse(raw)
            assert result["count"] == len(result["findings"])


class TestParserEmptyAndWhitespaceInput:
    """Parser must not crash and must return empty results for blank inputs."""

    def test_empty_string_does_not_crash(self, parser):
        assert parser.parse("") is not None

    def test_empty_string_returns_zero_findings(self, parser):
        result = parser.parse("")
        assert result["findings"] == []
        assert result["count"] == 0
        assert result["subdomains"] == []

    def test_whitespace_only_does_not_crash(self, parser):
        assert parser.parse("   \n  \n  ") is not None

    def test_whitespace_only_returns_zero_findings(self, parser):
        result = parser.parse("   \n  \n  ")
        assert result["findings"] == []
        assert result["count"] == 0
        assert result["subdomains"] == []

    def test_trailing_newlines_are_ignored(self, parser):
        result = parser.parse("api.example.com\n\n\n")
        assert result["count"] == 1
        assert result["subdomains"] == ["api.example.com"]

    def test_leading_and_trailing_blank_lines_are_ignored(self, parser):
        assert parser.parse("\n\napi.example.com\n\n")["count"] == 1


class TestParserSingleSubdomain:
    """Parser must handle a single-line input correctly."""

    def test_single_subdomain_count(self, parser):
        assert parser.parse("mail.example.com")["count"] == 1

    def test_single_subdomain_in_list(self, parser):
        assert parser.parse("mail.example.com")["subdomains"] == ["mail.example.com"]

    def test_single_subdomain_finding_shape(self, parser):
        result = parser.parse("mail.example.com")
        _assert_finding_shape(result["findings"][0], "mail.example.com")

    def test_single_subdomain_with_surrounding_whitespace(self, parser):
        result = parser.parse("  mail.example.com  ")
        assert result["count"] == 1
        assert result["subdomains"] == ["mail.example.com"]


class TestParserMalformedAndEdgeCaseInput:
    """Parser must not raise for unexpected or malformed input."""

    def test_non_domain_lines_do_not_crash(self, parser):
        assert parser.parse("not-a-domain\n!!bad!!\n123\n") is not None

    def test_non_domain_lines_still_produce_findings(self, parser):
        result = parser.parse("not-a-domain\n!!bad!!\n123")
        assert result["count"] == 3
        assert len(result["findings"]) == 3

    def test_mixed_valid_and_invalid_lines_do_not_crash(self, parser):
        result = parser.parse("api.example.com\n\n!!garbage!!\nsub.example.com")
        assert result["count"] == 3

    def test_very_long_single_line_does_not_crash(self, parser):
        long_line = "a" * 1000 + ".example.com"
        result = parser.parse(long_line)
        assert result["count"] == 1
        assert result["subdomains"] == [long_line]

    def test_many_subdomains_performance(self, parser):
        many = "\n".join(f"sub{i}.example.com" for i in range(500))
        result = parser.parse(many)
        assert result["count"] == 500
        assert len(result["findings"]) == 500