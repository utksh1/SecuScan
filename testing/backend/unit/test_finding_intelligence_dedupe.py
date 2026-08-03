"""
Unit tests for _dedupe_evidence and _merge_text in
backend/secuscan/finding_intelligence.py.

Run with:
    python3 -m pytest testing/backend/unit/test_finding_intelligence_dedupe.py -v --noconftest
"""

import pytest
from backend.secuscan import finding_intelligence as fi


# section _dedupe_evidence

class TestDedupeEvidence:
    def test_removes_exact_duplicates(self):
        item = {
            "type": "http_response",
            "label": "HTTP Response",
            "value": "200 OK",
            "artifact_ref": None,
            "source": "nuclei",
        }
        items = [item, item, item]
        result = fi._dedupe_evidence(items)
        assert len(result) == 1

    def test_preserves_different_values(self):
        items = [
            {"type": "http", "label": "A", "value": "1", "artifact_ref": None, "source": "n"},
            {"type": "http", "label": "A", "value": "2", "artifact_ref": None, "source": "n"},
        ]
        result = fi._dedupe_evidence(items)
        assert len(result) == 2

    def test_different_source_are_distinct(self):
        items = [
            {"type": "http", "label": "A", "value": "same", "artifact_ref": None, "source": "nuclei"},
            {"type": "http", "label": "A", "value": "same", "artifact_ref": None, "source": "nmap"},
        ]
        result = fi._dedupe_evidence(items)
        assert len(result) == 2

    def test_preserves_first_occurrence_order(self):
        first = {"type": "e", "label": "L", "value": "V", "artifact_ref": None, "source": "s"}
        second = {"type": "e", "label": "L", "value": "V", "artifact_ref": None, "source": "s"}
        result = fi._dedupe_evidence([second, first])
        assert result[0] is second

    def test_empty_list(self):
        assert fi._dedupe_evidence([]) == []

    def test_generator_input(self):
        def gen():
            yield {"type": "e", "label": "L", "value": "V", "artifact_ref": None, "source": "s"}
            yield {"type": "e", "label": "L", "value": "V", "artifact_ref": None, "source": "s"}

        result = fi._dedupe_evidence(gen())
        assert len(result) == 1

    def test_different_artifact_refs_are_distinct(self):
        items = [
            {"type": "e", "label": "L", "value": "V", "artifact_ref": "art-1", "source": "s"},
            {"type": "e", "label": "L", "value": "V", "artifact_ref": "art-2", "source": "s"},
        ]
        result = fi._dedupe_evidence(items)
        assert len(result) == 2


# section _merge_text

class TestMergeText:
    def test_primary_returned_when_non_empty(self):
        assert fi._merge_text("primary text", "fallback") == "primary text"

    def test_fallback_when_primary_empty(self):
        assert fi._merge_text("", "fallback") == "fallback"

    def test_fallback_when_primary_whitespace_only(self):
        assert fi._merge_text("   ", "fallback") == "fallback"

    def test_fallback_when_primary_none(self):
        assert fi._merge_text(None, "fallback") == "fallback"

    def test_primary_whitespace_preserved(self):
        result = fi._merge_text("  leading spaces  ", "fallback")
        assert result == "  leading spaces  "

    def test_both_empty_returns_empty(self):
        result = fi._merge_text("", "")
        assert result == ""

    def test_both_none_returns_none(self):
        result = fi._merge_text(None, None)
        assert result is None
