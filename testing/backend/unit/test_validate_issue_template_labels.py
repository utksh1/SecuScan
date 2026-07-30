import os
import sys

# Add root directory to sys.path so we can import from scripts
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

from scripts.validate_issue_template_labels import (
    extract_front_matter,
    parse_labels,
    extract_labels_from_front_matter,
)


def test_extract_front_matter_returns_content_between_markers():
    content = """---
labels: type:bug
---
body
"""
    assert extract_front_matter(content).strip() == "labels: type:bug"


def test_extract_front_matter_returns_empty_when_missing():
    assert extract_front_matter("no front matter") == ""


def test_parse_labels_inline_list():
    labels = parse_labels("[type:bug, area:backend, priority:high]")
    assert labels == ["type:bug", "area:backend", "priority:high"]


def test_parse_labels_with_quotes():
    labels = parse_labels('"type:testing","area:ci"')
    assert labels == ["type:testing", "area:ci"]


def test_extract_labels_single_line():
    front_matter = """
labels: [type:testing, area:ci]
"""
    assert extract_labels_from_front_matter(front_matter) == [
        "type:testing",
        "area:ci",
    ]


def test_extract_labels_multiline_yaml_list():
    front_matter = """
labels:
  - type:testing
  - area:ci
  - priority:medium
"""
    assert extract_labels_from_front_matter(front_matter) == [
        "type:testing",
        "area:ci",
        "priority:medium",
    ]


def test_extract_labels_returns_empty_when_missing():
    assert extract_labels_from_front_matter("title: example") == []