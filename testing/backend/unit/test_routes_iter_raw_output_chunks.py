"""
Unit tests for iter_raw_output_chunks in backend/secuscan/routes.py.

Tests the SSE chunk streaming helper for raw task output replay.
"""

import pytest
from backend.secuscan.routes_iter_helpers import iter_raw_output_chunks


class TestIterRawOutputChunks:
    def test_empty_file_yields_zero_chunks(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("")
        chunks = list(iter_raw_output_chunks(str(path)))
        assert chunks == []

    def test_single_chunk_smaller_than_size(self, tmp_path):
        path = tmp_path / "small.txt"
        content = "hello world"
        path.write_text(content)
        chunks = list(iter_raw_output_chunks(str(path)))
        assert len(chunks) == 1
        assert chunks[0] == content

    def test_exactly_chunk_size_yields_one_chunk(self, tmp_path):
        path = tmp_path / "exact.txt"
        # SSE_RAW_OUTPUT_CHUNK_SIZE = 64 * 1024
        chunk_size = 64 * 1024
        content = "x" * chunk_size
        path.write_text(content)
        chunks = list(iter_raw_output_chunks(str(path), chunk_size=chunk_size))
        assert len(chunks) == 1
        assert chunks[0] == content

    def test_chunk_size_plus_one_yields_two_chunks(self, tmp_path):
        path = tmp_path / "plus_one.txt"
        chunk_size = 64 * 1024
        content = "y" * (chunk_size + 1)
        path.write_text(content)
        chunks = list(iter_raw_output_chunks(str(path), chunk_size=chunk_size))
        assert len(chunks) == 2
        assert chunks[0] == "y" * chunk_size
        assert chunks[1] == "y"

    def test_multiple_chunks_for_large_file(self, tmp_path):
        path = tmp_path / "large.txt"
        chunk_size = 16
        # 3 full chunks + 1 partial
        content = "z" * (chunk_size * 3 + 5)
        path.write_text(content)
        chunks = list(iter_raw_output_chunks(str(path), chunk_size=chunk_size))
        assert len(chunks) == 4
        assert chunks[0] == "z" * chunk_size
        assert chunks[1] == "z" * chunk_size
        assert chunks[2] == "z" * chunk_size
        assert chunks[3] == "z" * 5

    def test_custom_chunk_size_respected(self, tmp_path):
        path = tmp_path / "custom.txt"
        content = "abc"
        path.write_text(content)
        chunks = list(iter_raw_output_chunks(str(path), chunk_size=2))
        assert len(chunks) == 2
        assert chunks[0] == "ab"
        assert chunks[1] == "c"

    def test_newlines_preserved_not_merged(self, tmp_path):
        path = tmp_path / "lines.txt"
        content = "line1\nline2\nline3"
        path.write_text(content)
        chunks = list(iter_raw_output_chunks(str(path)))
        assert len(chunks) == 1
        assert chunks[0] == content
        assert "\n" in chunks[0]

    def test_nonexistent_path_raises(self, tmp_path):
        nonexistent = str(tmp_path / "does_not_exist.txt")
        with pytest.raises(FileNotFoundError):
            list(iter_raw_output_chunks(nonexistent))

    def test_binary_file_with_replace_error_handling(self, tmp_path):
        path = tmp_path / "binary.bin"
        # Write bytes that would fail strict UTF-8 decoding
        path.write_bytes(b"hello\xffworld")
        chunks = list(iter_raw_output_chunks(str(path)))
        assert len(chunks) == 1
        # errors='replace' substitutes the replacement char
        assert "hello" in chunks[0]
        assert "world" in chunks[0]
