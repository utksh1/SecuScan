"""
Unit tests for scripts/validate_doc_links.py

Covers the three failure cases the documentation link validator must catch:
  1. Relative links to files that exist (should pass, no error).
  2. Links to missing files (should report a broken link).
  3. Links with a #fragment whose heading anchor is missing (broken anchor).
"""

import importlib.util
import pathlib

import pytest


# ── Load the script module by file path (it lives in scripts/, not a package) ──
def _load_validator():
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "scripts" / "validate_doc_links.py"
        if candidate.exists():
            spec = importlib.util.spec_from_file_location(
                "validate_doc_links", candidate
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise FileNotFoundError("scripts/validate_doc_links.py not found")


vdl = _load_validator()


# ── slugify: pure function, quick sanity check ────────────────────────────────
def test_slugify_matches_github_style():
    assert vdl.slugify("Setup Guide") == "setup-guide"
    assert vdl.slugify("Quick Start!") == "quick-start"


# ── Case 1: a valid relative link + valid anchor → no errors ──────────────────
def test_valid_relative_link_and_anchor(tmp_path, monkeypatch):
    monkeypatch.setattr(vdl, "REPO_ROOT", tmp_path.resolve())

    target = tmp_path / "guide.md"
    target.write_text("# Setup Guide\n\nsome text\n", encoding="utf-8")

    src = tmp_path / "README.md"
    src.write_text("[guide](guide.md#setup-guide)\n", encoding="utf-8")

    errors = vdl.validate_file(src)
    assert errors == []


# ── Case 2: link to a missing file → one "broken link target" error ───────────
def test_missing_file_link_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(vdl, "REPO_ROOT", tmp_path.resolve())

    src = tmp_path / "README.md"
    src.write_text("[docs](docs/does_not_exist.md)\n", encoding="utf-8")

    errors = vdl.validate_file(src)
    assert len(errors) == 1
    assert "broken link target" in errors[0]


# ── Case 3: link with a broken #anchor → one "anchor ... not found" error ──────
def test_broken_anchor_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(vdl, "REPO_ROOT", tmp_path.resolve())

    target = tmp_path / "guide.md"
    target.write_text("# Real Heading\n", encoding="utf-8")

    src = tmp_path / "README.md"
    src.write_text("[guide](guide.md#nonexistent-heading)\n", encoding="utf-8")

    errors = vdl.validate_file(src)
    assert len(errors) == 1
    assert "anchor" in errors[0]


# ── External URLs, in-page anchors, mailto links are skipped (no false errors) ─
def test_external_and_inpage_links_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(vdl, "REPO_ROOT", tmp_path.resolve())

    src = tmp_path / "README.md"
    src.write_text(
        "[web](https://example.com) [top](#intro) [mail](mailto:a@b.com)\n",
        encoding="utf-8",
    )

    errors = vdl.validate_file(src)
    assert errors == []