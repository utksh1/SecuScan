"""
Unit tests for extract_code_context edge cases in backend/secuscan/triage_engine.py.

Extends test_triage_engine.py with genuinely-missing edge cases:
- Non-UTF8 binary content in source file
- Very long single line (>10k chars)
- Empty proof string
- Proof with only whitespace
- Source file with fewer lines than context window
"""

from __future__ import annotations

import pytest
from pathlib import Path

from backend.secuscan.triage_engine import extract_code_context


class TestExtractCodeContextBinaryContent:
    def test_non_utf8_file_reads_with_replace(self, tmp_path):
        """Binary bytes that cannot be decoded should use errors='replace'."""
        source = tmp_path / "binary.py"
        # Write a file with a UTF-8 BOM and some invalid bytes
        source.write_bytes(b"\xef\xbb\xbfprint('hello')\n\x80\x81\x82")
        finding = {
            "title": "Test",
            "metadata": {"file": str(source), "line": 1},
        }
        result = extract_code_context(finding)
        # Should not raise; snippet should be a string
        assert isinstance(result["snippet"], str)

    def test_file_with_null_bytes(self, tmp_path):
        """Files containing null bytes should be readable."""
        source = tmp_path / "nulls.py"
        source.write_bytes(b"x = 1\n\x00\x00\x00\ny = 2\n")
        finding = {
            "title": "Test",
            "metadata": {"file": str(source), "line": 2},
        }
        result = extract_code_context(finding)
        # Should return a string snippet, not crash
        assert isinstance(result["snippet"], str)


class TestExtractCodeContextLongLine:
    def test_very_long_single_line(self, tmp_path):
        """A file with a single very long line (10k+ chars) should be handled."""
        long_line = "x = " + '"' + "a" * 20000 + '"'
        source = tmp_path / "long.py"
        source.write_text(long_line)
        finding = {
            "title": "Test",
            "metadata": {"file": str(source), "line": 1},
        }
        result = extract_code_context(finding)
        assert isinstance(result["snippet"], str)
        assert len(result["snippet"]) > 10000


class TestExtractCodeContextEmptyProof:
    def test_empty_proof_string(self):
        """An empty proof string should return empty snippet (not crash)."""
        finding = {
            "title": "Test finding",
            "proof": "",
            "metadata": {},
        }
        result = extract_code_context(finding)
        assert result["snippet"] == ""


class TestExtractCodeContextWhitespaceOnly:
    def test_proof_with_only_whitespace(self):
        """A proof string containing only spaces/tabs/newlines should not crash."""
        finding = {
            "title": "Test",
            "proof": "   \n\n   \t  ",
            "metadata": {},
        }
        result = extract_code_context(finding)
        assert result["snippet"].strip() == ""


class TestExtractCodeContextShortFile:
    def test_file_with_fewer_lines_than_context_window(self, tmp_path):
        """If the file has fewer lines than 2*CONTEXT_WINDOW, return all lines."""
        source = tmp_path / "short.py"
        source.write_text("line1\nline2\nline3\n")
        finding = {
            "title": "Test",
            "metadata": {"file": str(source), "line": 2},
        }
        result = extract_code_context(finding)
        assert "line1" in result["snippet"]
        assert "line2" in result["snippet"]
        assert "line3" in result["snippet"]


class TestExtractCodeContextMetadataVariants:
    def test_metadata_with_filename_instead_of_file(self, tmp_path):
        """Finding metadata uses 'filename' key instead of 'file'."""
        source = tmp_path / "test.py"
        source.write_text("def foo():\n    pass\n")
        finding = {
            "title": "Test",
            "metadata": {"filename": str(source), "line": 1},
        }
        result = extract_code_context(finding)
        assert result["file"] == str(source)

    def test_metadata_with_line_number_instead_of_line(self, tmp_path):
        """Finding metadata uses 'line_number' key instead of 'line'."""
        source = tmp_path / "test.py"
        source.write_text("a\nb\nc\nd\ne\nf\ng\nh\n")
        finding = {
            "title": "Test",
            "metadata": {"file": str(source), "line_number": 3},
        }
        result = extract_code_context(finding)
        # Should use line 3 as center of context window
        assert result["line"] == 3


class TestExtractCodeContextNonDictMetadata:
    def test_metadata_not_a_dict(self):
        """Non-dict metadata (e.g. list) should fall back gracefully."""
        finding = {
            "title": "Test",
            "proof": "x = 1",
            "metadata": "not a dict",
        }
        result = extract_code_context(finding)
        assert result["file"] == ""


class TestExtractCodeContextVariables:
    def test_variables_extracted_from_proof(self):
        """Variables from proof should be extracted into context."""
        finding = {
            "title": "Issue",
            "proof": "sql_query = f'SELECT {user_id}'\nurl = request.args.get('url')",
            "metadata": {},
        }
        result = extract_code_context(finding)
        assert "sql_query" in result["variables"]
        assert "url" in result["variables"]

    def test_variables_capped_at_10(self):
        """Variables list should be capped at 10 entries."""
        many_assignments = "\n".join(f"var{i} = {i}" for i in range(15))
        finding = {
            "title": "Issue",
            "proof": many_assignments,
            "metadata": {},
        }
        result = extract_code_context(finding)
        assert len(result["variables"]) <= 10
