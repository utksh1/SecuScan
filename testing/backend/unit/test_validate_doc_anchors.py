from scripts.validate_doc_anchors import slugify, validate_file


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


def test_slugify_heading():
    assert slugify("Incident Response Runbook") == "incident-response-runbook"


def test_slugify_special_chars():
    assert slugify("Hello, World!") == "hello-world"
