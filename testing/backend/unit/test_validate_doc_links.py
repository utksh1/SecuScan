"""
Unit tests for scripts/validate_doc_links.py

Tests the pure helper functions: slugify, collect_anchors, source_files,
and validate_file.
"""

import sys
import pathlib
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent / "scripts"))
import validate_doc_links
from validate_doc_links import slugify, collect_anchors, source_files

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent


class TestSlugify:
    def test_lowercases(self):
        assert slugify("Hello World") == "hello-world"

    def test_strips_non_alphanumeric(self):
        assert slugify("API v2!") == "api-v2"

    def test_collapse_spaces(self):
        # re.sub(r"\s+", "-", ...) replaces ALL whitespace runs with one dash
        assert slugify("multi  space") == "multi-space"

    def test_strip_leading_trailing_whitespace(self):
        assert slugify("  padded  ") == "padded"

    def test_preserve_hyphens(self):
        assert slugify("step-1-of-3") == "step-1-of-3"

    def test_unicode_is_preserved(self):
        assert slugify("plugin-name") == "plugin-name"

    def test_empty_string_returns_empty(self):
        assert slugify("") == ""

    def test_single_word(self):
        assert slugify("Overview") == "overview"


class TestCollectAnchors:
    def test_single_h1(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Hello World\nSome content.\n")
        anchors = collect_anchors(f)
        assert "hello-world" in anchors

    def test_h2_creates_anchor(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("## API Reference\nContent here.\n")
        anchors = collect_anchors(f)
        assert "api-reference" in anchors

    def test_multiple_headings(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Alpha\n## Beta\n### Gamma\n")
        anchors = collect_anchors(f)
        assert "alpha" in anchors
        assert "beta" in anchors
        assert "gamma" in anchors

    def test_code_block_not_extracted(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Valid\n```\n# Not a Heading\n```\n")
        anchors = collect_anchors(f)
        assert "valid" in anchors

    def test_empty_file_returns_empty_set(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        anchors = collect_anchors(f)
        assert anchors == set()


class TestSourceFiles:
    def test_returns_list(self):
        files = source_files()
        assert isinstance(files, list)

    def test_readme_is_included(self):
        files = source_files()
        paths = [str(f) for f in files]
        assert any("README.md" in p for p in paths)

    def test_docs_subdirectory_included(self):
        files = source_files()
        paths = [str(f) for f in files]
        assert any("docs/" in p for p in paths)

    def test_only_markdown_files(self):
        files = source_files()
        for f in files:
            assert f.suffix == ".md"


class TestValidateFile:
    def test_no_links_returns_empty(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Test\nNo links here.\n")
        errors = validate_doc_links.validate_file(f)
        assert errors == []

    def test_external_url_skipped(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Test\n[Link](https://example.com)\n")
        errors = validate_doc_links.validate_file(f)
        assert errors == []

    def test_mailto_skipped(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Test\n[Email](mailto:test@example.com)\n")
        errors = validate_doc_links.validate_file(f)
        assert errors == []

    def test_page_anchor_skipped(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Test\n[Jump](#section)\n")
        errors = validate_doc_links.validate_file(f)
        assert errors == []

    def test_broken_link_with_repo_root(self, tmp_path, monkeypatch):
        # validate_file uses REPO_ROOT from the module; patch it to tmp_path
        monkeypatch.setattr(validate_doc_links, "REPO_ROOT", tmp_path)
        f = tmp_path / "test.md"
        f.write_text("# Test\n[Link](nonexistent.md)\n")
        errors = validate_doc_links.validate_file(f)
        assert len(errors) == 1

    def test_broken_anchor_with_repo_root(self, tmp_path, monkeypatch):
        monkeypatch.setattr(validate_doc_links, "REPO_ROOT", tmp_path)
        target = tmp_path / "target.md"
        target.write_text("# Real Anchor\n")
        source = tmp_path / "source.md"
        source.write_text("# Source\n[Link](target.md#nonexistent)\n")
        errors = validate_doc_links.validate_file(source)
        assert len(errors) == 1
        assert "anchor" in errors[0].lower()

    def test_valid_link_with_repo_root(self, tmp_path, monkeypatch):
        monkeypatch.setattr(validate_doc_links, "REPO_ROOT", tmp_path)
        target = tmp_path / "target.md"
        target.write_text("# Target\n")
        source = tmp_path / "source.md"
        source.write_text("# Source\n[Link](target.md#target)\n")
        errors = validate_doc_links.validate_file(source)
        assert errors == []
