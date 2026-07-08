"""
Unit tests for finding_intelligence confidence and severity helper functions.

Covers:
- _normalize_severity: maps severity strings to canonical labels
- _severity_rank: returns comparable integer rank for severity
- _source_quality: scores source reliability from SOURCE_QUALITY map
- _fingerprint_score: returns (score, match_strength) from finding metadata
- _build_confidence_reason: composes human-readable confidence explanation
- _compute_confidence: combines multiple factors into a 0-1 confidence score
- _sort_sources: sorts and deduplicates source strings
"""

from __future__ import annotations

import pytest

from backend.secuscan.finding_intelligence import (
    _normalize_severity,
    _severity_rank,
    _source_quality,
    _fingerprint_score,
    _build_confidence_reason,
    _compute_confidence,
    _sort_sources,
)


# ---------------------------------------------------------------------------
# _normalize_severity
# ---------------------------------------------------------------------------

class TestNormalizeSeverity:
    def test_known_severities(self):
        assert _normalize_severity("critical") == "critical"
        assert _normalize_severity("high") == "high"
        assert _normalize_severity("medium") == "medium"
        assert _normalize_severity("moderate") == "medium"
        assert _normalize_severity("low") == "low"
        assert _normalize_severity("info") == "info"
        assert _normalize_severity("informational") == "info"
        assert _normalize_severity("note") == "info"

    def test_case_insensitive(self):
        assert _normalize_severity("CRITICAL") == "critical"
        assert _normalize_severity("High") == "high"
        assert _normalize_severity("MeDiUm") == "medium"

    def test_unknown_defaults_to_info(self):
        assert _normalize_severity("unknown") == "info"
        assert _normalize_severity("") == "info"
        assert _normalize_severity(None) == "info"


# ---------------------------------------------------------------------------
# _severity_rank
# ---------------------------------------------------------------------------

class TestSeverityRank:
    def test_rank_order(self):
        assert _severity_rank("critical") == 5
        assert _severity_rank("high") == 4
        assert _severity_rank("medium") == 3
        assert _severity_rank("low") == 2
        assert _severity_rank("info") == 1

    def test_unknown_defaults_to_info_rank(self):
        assert _severity_rank("unknown") == 1
        assert _severity_rank("") == 1
        assert _severity_rank(None) == 1

    def test_rank_is_comparable(self):
        assert _severity_rank("critical") > _severity_rank("high")
        assert _severity_rank("high") > _severity_rank("medium")
        assert _severity_rank("medium") > _severity_rank("low")
        assert _severity_rank("low") > _severity_rank("info")


# ---------------------------------------------------------------------------
# _source_quality
# ---------------------------------------------------------------------------

class TestSourceQuality:
    def test_known_sources(self):
        assert _source_quality(["nuclei"]) == 0.8
        assert _source_quality(["nikto"]) == 0.7
        assert _source_quality(["nmap"]) == 0.78
        assert _source_quality(["http_probe"]) == 0.82

    def test_multiple_sources_returns_max(self):
        assert _source_quality(["nikto", "nuclei"]) == 0.8
        assert _source_quality(["crawl", "openapi"]) == 0.8

    def test_unknown_source_uses_default(self):
        assert _source_quality(["unknown_scanner"]) == 0.58

    def test_empty_source_list(self):
        assert _source_quality([]) == 0.58

    def test_whitespace_source_uses_default(self):
        assert _source_quality(["  "]) == 0.58


# ---------------------------------------------------------------------------
# _fingerprint_score
# ---------------------------------------------------------------------------

class TestFingerprintScore:
    def test_validated_match(self):
        score, strength = _fingerprint_score({"validated": True})
        assert score == 1.0
        assert strength == "validated"

    def test_exact_match(self):
        score, strength = _fingerprint_score(
            {"metadata": {"match_strength": "exact"}}
        )
        assert score == 0.95
        assert strength == "exact"

    def test_strong_fuzzy(self):
        score, strength = _fingerprint_score(
            {"metadata": {"match_strength": "strong_fuzzy"}}
        )
        assert score == 0.8
        assert strength == "strong_fuzzy"

    def test_fuzzy(self):
        score, strength = _fingerprint_score(
            {"metadata": {"match_strength": "fuzzy"}}
        )
        assert score == 0.7
        assert strength == "fuzzy"

    def test_family(self):
        score, strength = _fingerprint_score(
            {"metadata": {"match_strength": "family"}}
        )
        assert score == 0.45
        assert strength == "family"

    def test_none_match(self):
        score, strength = _fingerprint_score({"metadata": {}})
        assert score == 0.25
        assert strength == "none"

    def test_missing_metadata(self):
        score, strength = _fingerprint_score({})
        assert score == 0.25
        assert strength == "none"


# ---------------------------------------------------------------------------
# _build_confidence_reason
# ---------------------------------------------------------------------------

class TestBuildConfidenceReason:
    def test_basic_reason(self):
        result = _build_confidence_reason(
            finding_kind="observation",
            evidence_count=3,
            corroborating_sources=["nuclei"],
            occurrence_count=1,
            match_strength="none",
        )
        assert "Observation" in result
        assert "3 evidence items" in result
        assert "1 source" in result
        assert result.endswith(".")

    def test_singular_evidence(self):
        result = _build_confidence_reason(
            finding_kind="suspected_issue",
            evidence_count=1,
            corroborating_sources=[],
            occurrence_count=1,
            match_strength="none",
        )
        assert "evidence item" in result

    def test_multiple_occurrences(self):
        result = _build_confidence_reason(
            finding_kind="validated_issue",
            evidence_count=5,
            corroborating_sources=["nuclei", "nmap"],
            occurrence_count=3,
            match_strength="fuzzy",
        )
        assert "3 scan observations" in result

    def test_fingerprint_match(self):
        result = _build_confidence_reason(
            finding_kind="suspected_issue",
            evidence_count=2,
            corroborating_sources=[],
            occurrence_count=1,
            match_strength="exact",
        )
        assert "exact fingerprint match" in result

    def test_empty_match_strength(self):
        result = _build_confidence_reason(
            finding_kind="observation",
            evidence_count=2,
            corroborating_sources=[],
            occurrence_count=1,
            match_strength="",
        )
        assert result  # should not crash


# ---------------------------------------------------------------------------
# _compute_confidence
# ---------------------------------------------------------------------------

class TestComputeConfidence:
    def test_returns_float_in_valid_range(self):
        score = _compute_confidence(
            {},
            corroborating_sources=["nuclei"],
            occurrence_count=1,
            evidence=[],
        )
        assert 0.0 <= score <= 0.99
        assert isinstance(score, float)

    def test_high_value_sources_increase_score(self):
        low = _compute_confidence(
            {},
            corroborating_sources=["nikto"],
            occurrence_count=1,
            evidence=[],
        )
        high = _compute_confidence(
            {},
            corroborating_sources=["openapi"],
            occurrence_count=1,
            evidence=[],
        )
        assert high > low

    def test_more_evidence_increases_score(self):
        no_evidence = _compute_confidence(
            {},
            corroborating_sources=[],
            occurrence_count=1,
            evidence=[],
        )
        with_evidence = _compute_confidence(
            {},
            corroborating_sources=[],
            occurrence_count=1,
            evidence=[{}, {}, {}, {}],
        )
        assert with_evidence > no_evidence

    def test_more_occurrences_increases_score(self):
        single = _compute_confidence(
            {},
            corroborating_sources=[],
            occurrence_count=1,
            evidence=[],
        )
        repeated = _compute_confidence(
            {},
            corroborating_sources=[],
            occurrence_count=5,
            evidence=[],
        )
        assert repeated > single

    def test_validated_finding_increases_score(self):
        unvalidated = _compute_confidence(
            {"validated": False},
            corroborating_sources=[],
            occurrence_count=1,
            evidence=[],
        )
        validated = _compute_confidence(
            {"validated": True},
            corroborating_sources=[],
            occurrence_count=1,
            evidence=[],
        )
        assert validated > unvalidated

    def test_critical_severity_increases_score(self):
        info = _compute_confidence(
            {"severity": "info"},
            corroborating_sources=[],
            occurrence_count=1,
            evidence=[],
        )
        critical = _compute_confidence(
            {"severity": "critical"},
            corroborating_sources=[],
            occurrence_count=1,
            evidence=[],
        )
        assert critical > info

    def test_score_is_capped_at_0_99(self):
        # Very strong finding
        score = _compute_confidence(
            {"validated": True, "severity": "critical"},
            corroborating_sources=["openapi", "graphql", "nuclei"],
            occurrence_count=10,
            evidence=[{}, {}, {}, {}],
        )
        assert score <= 0.99


# ---------------------------------------------------------------------------
# _sort_sources
# ---------------------------------------------------------------------------

class TestSortSources:
    def test_removes_duplicates(self):
        result = _sort_sources(["nuclei", "nuclei", "nikto"])
        assert result == ["nikto", "nuclei"]

    def test_sorts_alphabetically(self):
        result = _sort_sources(["zap", "nuclei", "nikto"])
        assert result == ["nikto", "nuclei", "zap"]

    def test_whitespace_is_stripped(self):
        result = _sort_sources(["  nuclei  ", "nikto"])
        assert "nuclei" in result
        assert "  nuclei  " not in result

    def test_empty_and_whitespace_removed(self):
        result = _sort_sources(["nuclei", "", "  ", None])
        assert "nuclei" in result
        assert "" not in result
        assert "  " not in result
