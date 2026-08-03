from scripts.validate_doc_anchors import (
    LinkIssue,
    slugify,
    validate_file,
    validate_markdown_references,
)

def test_detects_missing_anchor(tmp_path):
    doc = tmp_path / "sample.md"

    doc.write_text(
        "# Heading\n\n[Broken](#missing-anchor)\n",
        encoding="utf-8",
    )

    failures = validate_file(doc)

    assert failures == ["missing-anchor"]


def test_valid_anchor_passes(tmp_path):
    doc = tmp_path / "sample.md"

    doc.write_text(
        "# My Heading\n\n[Link](#my-heading)\n",
        encoding="utf-8",
    )

    failures = validate_file(doc)

    assert failures == []


def test_valid_relative_file_link_passes(tmp_path):
    readme = tmp_path / "README.md"
    guide = tmp_path / "guide.md"

    readme.write_text("[Guide](guide.md)\n", encoding="utf-8")
    guide.write_text("# Guide\n", encoding="utf-8")

    issues = validate_markdown_references(readme, {})

    assert issues == []


def test_missing_file_is_reported(tmp_path):
    readme = tmp_path / "README.md"

    readme.write_text("[Broken](missing.md)\n", encoding="utf-8")

    issues = validate_markdown_references(readme, {})

    assert issues == [LinkIssue(target="missing.md", missing_file=True)]


def test_valid_file_anchor_passes(tmp_path):
    readme = tmp_path / "README.md"
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    api = docs_dir / "API.md"

    readme.write_text("[API](docs/API.md#authentication-flow)\n", encoding="utf-8")
    api.write_text("# Authentication Flow\n", encoding="utf-8")

    issues = validate_markdown_references(readme, {})

    assert issues == []


def test_missing_anchor_in_other_file_is_reported(tmp_path):
    readme = tmp_path / "README.md"
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    api = docs_dir / "API.md"

    readme.write_text("[API](docs/API.md#authentication-flow)\n", encoding="utf-8")
    api.write_text("# Overview\n", encoding="utf-8")

    issues = validate_markdown_references(readme, {})

    assert issues == [
        LinkIssue(target="docs/API.md", missing_anchor="authentication-flow")
    ]


def test_external_url_is_ignored(tmp_path):
    readme = tmp_path / "README.md"

    readme.write_text("[Docs](https://example.com)\n", encoding="utf-8")

    issues = validate_markdown_references(readme, {})

    assert issues == []


def test_image_markdown_is_ignored(tmp_path):
    readme = tmp_path / "README.md"

    readme.write_text("![](image.png)\n", encoding="utf-8")

    issues = validate_markdown_references(readme, {})

    assert issues == []

def test_slugify_heading():
    assert slugify("Incident Response Runbook") == "incident-response-runbook"


def test_slugify_special_chars():
    assert slugify("Hello, World!") == "hello-world"
