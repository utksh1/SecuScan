"""
Unit tests for pure helper functions in backend/secuscan/finding_intelligence.py.

Run with:
    python3 -m pytest testing/backend/unit/test_finding_intelligence.py -v --noconftest
"""

import pytest
from backend.secuscan.finding_intelligence import (
    _normalize_severity,
    _severity_rank,
    _normalize_url_path,
    _extract_best_url,
    _guess_asset_ref,
    _issue_signature,
    _typed_evidence,
    _dedupe_evidence,
    _merge_text,
    _build_confidence_reason,
    _finding_kind_for,
    _fingerprint_score,
    _source_quality,
    _compute_confidence,
    _sort_sources,
    build_asset_summary,
    build_finding_groups,
    build_scan_diff,
)


# section normalize_severity

class TestNormalizeSeverity:
    def test_critical(self):
        assert _normalize_severity("critical") == "critical"

    def test_high(self):
        assert _normalize_severity("high") == "high"

    def test_medium(self):
        assert _normalize_severity("medium") == "medium"

    def test_moderate_alias(self):
        assert _normalize_severity("moderate") == "medium"

    def test_low(self):
        assert _normalize_severity("low") == "low"

    def test_info(self):
        assert _normalize_severity("info") == "info"

    def test_informational_alias(self):
        assert _normalize_severity("informational") == "info"

    def test_note_alias(self):
        assert _normalize_severity("note") == "info"

    def test_case_insensitive(self):
        assert _normalize_severity("CRITICAL") == "critical"
        assert _normalize_severity("High") == "high"

    def test_none_input_defaults_to_info(self):
        assert _normalize_severity(None) == "info"

    def test_empty_string_defaults_to_info(self):
        assert _normalize_severity("") == "info"

    def test_unknown_value_defaults_to_info(self):
        assert _normalize_severity("super-critical") == "info"


# section severity_rank

class TestSeverityRank:
    def test_rank_order(self):
        assert _severity_rank("critical") > _severity_rank("high")
        assert _severity_rank("high") > _severity_rank("medium")
        assert _severity_rank("medium") > _severity_rank("low")
        assert _severity_rank("low") > _severity_rank("info")

    def test_rank_returns_int(self):
        assert isinstance(_severity_rank("high"), int)

    def test_rank_unknown_defaults_to_info_rank(self):
        assert _severity_rank("unknown") == _severity_rank("info")

    def test_rank_aliases(self):
        assert _severity_rank("moderate") == _severity_rank("medium")
        assert _severity_rank("informational") == _severity_rank("info")


# section normalize_url_path

class TestNormalizeUrlPath:
    def test_full_url(self):
        assert _normalize_url_path("https://example.com/api/v1/users/") == "/api/v1/users"

    def test_full_url_trailing_slash_stripped(self):
        assert _normalize_url_path("http://example.com/") == "/"

    def test_path_only(self):
        assert _normalize_url_path("/api/v1/users") == "/api/v1/users"

    def test_path_only_preserved(self):
        assert _normalize_url_path("/api?foo=bar") == "/api?foo=bar"

    def test_empty_string(self):
        assert _normalize_url_path("") == ""

    def test_fragment_only(self):
        assert _normalize_url_path("#section") == ""


# section extract_best_url

class TestExtractBestUrl:
    def test_url_in_metadata_url(self):
        finding = {"metadata": {"url": "https://example.com/login"}}
        assert _extract_best_url(finding) == "https://example.com/login"

    def test_url_in_metadata_endpoint(self):
        finding = {"metadata": {"endpoint": "https://api.example.com/v2/data"}}
        assert _extract_best_url(finding) == "https://api.example.com/v2/data"

    def test_url_in_evidence(self):
        finding = {
            "evidence": [
                {"value": "https://example.com/admin"},
                {"value": "http://internal.local/file"},
            ]
        }
        assert _extract_best_url(finding) == "https://example.com/admin"

    def test_url_in_target(self):
        finding = {"target": "https://target.example.com/scan"}
        assert _extract_best_url(finding) == "https://target.example.com/scan"

    def test_target_http_prefix(self):
        finding = {"target": "http://example.com"}
        assert _extract_best_url(finding) == "http://example.com"

    def test_no_url_returns_empty(self):
        finding = {"target": "example.com"}
        assert _extract_best_url(finding) == ""

    def test_non_dict_evidence_skipped(self):
        finding = {
            "evidence": [
                "not a dict",
                {"value": "https://example.com/api"},
            ]
        }
        assert _extract_best_url(finding) == "https://example.com/api"

    def test_empty_metadata(self):
        finding = {}
        assert _extract_best_url(finding) == ""


# section guess_asset_ref

class TestGuessAssetRef:
    def test_asset_refs_takes_priority(self):
        finding = {"asset_refs": ["https://example.com/"]}
        assert _guess_asset_ref(finding, "https://fallback.com") == "https://example.com/"

    def test_url_in_finding_used_when_no_asset_refs(self):
        finding = {"metadata": {"url": "https://api.example.com/v1/"}}
        assert _guess_asset_ref(finding, "https://fallback.com") == "https://api.example.com/v1/"

    def test_host_port_protocol_from_metadata(self):
        finding = {"metadata": {"host": "server.example.com", "port": 443, "protocol": "https"}}
        result = _guess_asset_ref(finding, "https://fallback.com")
        assert "server.example.com" in result
        assert "443" in result

    def test_falls_back_to_target(self):
        finding = {}
        assert _guess_asset_ref(finding, "https://target.example.com/") == "https://target.example.com/"

    def test_strips_whitespace_from_asset_ref(self):
        finding = {"asset_refs": ["  https://example.com/api  "]}
        assert _guess_asset_ref(finding, "target") == "https://example.com/api"


# section issue_signature

class TestIssueSignature:
    def test_cve_finding(self):
        finding = {"cve": "CVE-2023-44487", "title": "Something else"}
        sig = _issue_signature(finding)
        assert sig.startswith("cve:cve-2023-44487")

    def test_signature_from_category_title_and_path(self):
        finding = {
            "category": "Transport Security",
            "title": "Missing CSP Header",
            "validation_method": "",
            "metadata": {},
        }
        sig = _issue_signature(finding)
        assert "transport-security" in sig
        assert "missing-csp-header" in sig

    def test_signature_includes_template(self):
        finding = {
            "category": "vulnerability",
            "title": "SQL Injection",
            "validation_method": "",
            "metadata": {"template": "sql-injection-test"},
        }
        sig = _issue_signature(finding)
        assert "sql-injection-test" in sig

    def test_signature_normalizes_whitespace(self):
        finding = {
            "category": "  Security  ",
            "title": "  Open Port  ",
            "validation_method": "",
            "metadata": {},
        }
        sig = _issue_signature(finding)
        assert sig == sig.strip().lower().replace("  ", "-")

    def test_empty_finding_returns_empty_components(self):
        finding = {}
        sig = _issue_signature(finding)
        # Empty components join to '||||'
        assert "finding" not in sig or sig == ""


# section typed_evidence

class TestTypedEvidence:
    def test_dict_item_with_all_fields(self):
        item = {
            "type": "http_response",
            "label": "HTTP Response",
            "value": "200 OK",
            "artifact_ref": "artifact-1",
            "source": "nuclei",
            "observed_at": "2024-01-01T00:00:00Z",
            "confidence": 0.95,
        }
        result = _typed_evidence(
            item,
            source="default_source",
            observed_at="2024-01-02T00:00:00Z",
            confidence=0.72,
        )
        assert result["type"] == "http_response"
        assert result["label"] == "HTTP Response"
        assert result["value"] == "200 OK"
        assert result["confidence"] == 0.95
        assert result["source"] == "nuclei"

    def test_dict_item_defaults_missing_fields(self):
        item = {"value": "some data"}
        result = _typed_evidence(item, source="nmap", observed_at="2024-01-01Z", confidence=0.8)
        assert result["type"] == "evidence"
        assert result["label"] == "Evidence"
        assert result["source"] == "nmap"
        assert result["confidence"] == 0.8

    def test_non_dict_item(self):
        item = "plain text finding"
        result = _typed_evidence(item, source="scanner", observed_at="2024-01-01Z", confidence=0.6)
        assert result["type"] == "evidence"
        assert result["label"] == "Evidence"
        assert result["value"] == "plain text finding"
        assert result["source"] == "scanner"

    def test_confidence_clamped_to_0_1(self):
        item = {"confidence": 1.5}
        result = _typed_evidence(item, source="s", observed_at="t", confidence=0.5)
        assert result["confidence"] == 1.0

        item2 = {"confidence": -0.5}
        result2 = _typed_evidence(item2, source="s", observed_at="t", confidence=0.5)
        assert result2["confidence"] == 0.0


# section dedupe_evidence

class TestDedupeEvidence:
    def test_removes_exact_duplicates(self):
        item = {"type": "http_response", "label": "Response", "value": "200 OK", "source": "nuclei"}
        items = [item, item, item]
        result = _dedupe_evidence(items)
        assert len(result) == 1

    def test_preserves_different_values(self):
        items = [
            {"type": "http", "label": "A", "value": "1", "source": "n"},
            {"type": "http", "label": "A", "value": "2", "source": "n"},
        ]
        result = _dedupe_evidence(items)
        assert len(result) == 2

    def test_different_source_are_distinct(self):
        items = [
            {"type": "http", "label": "A", "value": "same", "source": "nuclei"},
            {"type": "http", "label": "A", "value": "same", "source": "nmap"},
        ]
        result = _dedupe_evidence(items)
        assert len(result) == 2

    def test_empty_list(self):
        assert _dedupe_evidence([]) == []

    def test_generator_input(self):
        def gen():
            yield {"type": "e", "label": "L", "value": "V", "source": "s"}
            yield {"type": "e", "label": "L", "value": "V", "source": "s"}

        result = _dedupe_evidence(gen())
        assert len(result) == 1


# section merge_text

class TestMergeText:
    def test_primary_returned_when_non_empty(self):
        assert _merge_text("primary text", "fallback") == "primary text"

    def test_fallback_when_primary_empty(self):
        assert _merge_text("", "fallback") == "fallback"

    def test_fallback_when_primary_whitespace_only(self):
        assert _merge_text("   ", "fallback") == "fallback"

    def test_fallback_when_primary_none(self):
        assert _merge_text(None, "fallback") == "fallback"

    def test_primary_whitespace_not_stripped(self):
        result = _merge_text("  leading spaces  ", "fallback")
        assert result == "  leading spaces  "


# section build_confidence_reason

class TestBuildConfidenceReason:
    def test_basic(self):
        result = _build_confidence_reason(
            finding_kind="validated_issue",
            evidence_count=3,
            corroborating_sources=["nuclei", "nmap"],
            occurrence_count=1,
            match_strength="exact",
        )
        assert "issue classification" in result.lower()
        assert "3 evidence items" in result
        assert "corroborated by 2 sources" in result
        assert "exact fingerprint match" in result

    def test_single_source_no_plural(self):
        result = _build_confidence_reason(
            finding_kind="observation",
            evidence_count=1,
            corroborating_sources=["nmap"],
            occurrence_count=1,
            match_strength="none",
        )
        assert "1 evidence item" in result
        assert "1 source" in result

    def test_occurrence_count(self):
        result = _build_confidence_reason(
            finding_kind="suspected_issue",
            evidence_count=1,
            corroborating_sources=[],
            occurrence_count=5,
            match_strength="fuzzy",
        )
        assert "seen across 5 scan observations" in result

    def test_empty_corroborating_sources(self):
        result = _build_confidence_reason(
            finding_kind="observation",
            evidence_count=1,
            corroborating_sources=[],
            occurrence_count=1,
            match_strength="none",
        )
        assert "corroborated by" not in result

    def test_result_is_capitalized(self):
        result = _build_confidence_reason(
            finding_kind="observation",
            evidence_count=1,
            corroborating_sources=[],
            occurrence_count=1,
            match_strength="none",
        )
        assert result[0].isupper()


# section finding_kind_for

class TestFindingKindFor:
    def test_validated_high_severity_is_validated_issue(self):
        finding = {"validated": True, "severity": "high", "category": "sql_injection"}
        assert _finding_kind_for(finding) == "validated_issue"

    def test_observation_category_is_observation(self):
        finding = {"severity": "low", "category": "attack surface"}
        assert _finding_kind_for(finding) == "observation"

    def test_high_severity_no_cve_is_suspected_issue(self):
        finding = {"severity": "high", "category": "misc"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_cve_present_is_suspected_issue(self):
        finding = {"cve": "CVE-2023-44487", "severity": "info"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_cpe_cve_correlation_is_suspected_issue(self):
        finding = {"validation_method": "cpe_cve_correlation", "severity": "low"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_default_is_observation(self):
        finding = {"severity": "info"}
        assert _finding_kind_for(finding) == "observation"


# section fingerprint_score

class TestFingerprintScore:
    def test_validated_returns_1_0(self):
        finding = {"validated": True}
        score, strength = _fingerprint_score(finding)
        assert score == 1.0
        assert strength == "validated"

    def test_exact_match_strength(self):
        finding = {"metadata": {"match_strength": "exact"}}
        score, strength = _fingerprint_score(finding)
        assert score == 0.95
        assert strength == "exact"

    def test_fuzzy_match_strength(self):
        finding = {"metadata": {"cpe_match_strength": "fuzzy"}}
        score, strength = _fingerprint_score(finding)
        assert score == 0.7
        assert strength == "fuzzy"

    def test_family_match_strength(self):
        finding = {"metadata": {"match_strength": "family"}}
        score, strength = _fingerprint_score(finding)
        assert score == 0.45

    def test_no_match_strength_defaults_to_none(self):
        finding = {}
        score, strength = _fingerprint_score(finding)
        assert score == 0.25
        assert strength == "none"

    def test_returns_tuple(self):
        result = _fingerprint_score({})
        assert isinstance(result, tuple)
        assert len(result) == 2


# section source_quality

class TestSourceQuality:
    def test_returns_max_quality(self):
        sources = ["nuclei", "nmap", "custom_tool"]
        score = _source_quality(sources)
        assert isinstance(score, float)
        assert score >= 0

    def test_empty_sources_returns_default(self):
        score = _source_quality([])
        assert score == 0.58

    def test_whitespace_sources_ignored(self):
        score = _source_quality(["  ", "nuclei"])
        assert score == _source_quality(["nuclei"])

    def test_unknown_source_uses_default(self):
        score = _source_quality(["totally_unknown_scanner_xyz"])
        assert score == 0.58


# section compute_confidence

class TestComputeConfidence:
    def test_returns_float(self):
        finding = {"severity": "high", "validated": False}
        score = _compute_confidence(
            finding,
            corroborating_sources=["nuclei"],
            occurrence_count=1,
            evidence=[],
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 0.99

    def test_validated_finding_boosts_score(self):
        finding_v = {"severity": "high", "validated": True}
        finding_nv = {"severity": "high", "validated": False}
        score_v = _compute_confidence(finding_v, corroborating_sources=[], occurrence_count=1, evidence=[])
        score_nv = _compute_confidence(finding_nv, corroborating_sources=[], occurrence_count=1, evidence=[])
        assert score_v > score_nv

    def test_cve_present_boosts_score(self):
        finding_cve = {"severity": "info", "cve": "CVE-2023-44487"}
        finding_no_cve = {"severity": "info"}
        score_cve = _compute_confidence(finding_cve, corroborating_sources=[], occurrence_count=1, evidence=[])
        score_no_cve = _compute_confidence(finding_no_cve, corroborating_sources=[], occurrence_count=1, evidence=[])
        assert score_cve > score_no_cve

    def test_higher_severity_boosts_score(self):
        finding_h = {"severity": "high"}
        finding_l = {"severity": "low"}
        score_h = _compute_confidence(finding_h, corroborating_sources=[], occurrence_count=1, evidence=[])
        score_l = _compute_confidence(finding_l, corroborating_sources=[], occurrence_count=1, evidence=[])
        assert score_h > score_l

    def test_more_sources_boosts_score(self):
        finding = {"severity": "medium"}
        score_one = _compute_confidence(finding, corroborating_sources=["nmap"], occurrence_count=1, evidence=[])
        score_multi = _compute_confidence(finding, corroborating_sources=["nmap", "nuclei", "zap"], occurrence_count=1, evidence=[])
        assert score_multi > score_one

    def test_rounds_to_two_decimals(self):
        finding = {"severity": "critical", "validated": True}
        score = _compute_confidence(finding, corroborating_sources=["nuclei", "nmap"], occurrence_count=3, evidence=[{}, {}, {}])
        assert score == round(score, 2)


# section sort_sources

class TestSortSources:
    def test_removes_duplicates(self):
        sources = ["nmap", "nuclei", "nmap"]
        assert _sort_sources(sources) == ["nmap", "nuclei"]

    def test_sorts_alphabetically(self):
        sources = ["zap", "nmap", "nuclei"]
        assert _sort_sources(sources) == ["nmap", "nuclei", "zap"]

    def test_strips_whitespace(self):
        sources = ["  nuclei  ", "nmap"]
        assert _sort_sources(sources) == ["nmap", "nuclei"]

    def test_empty_list(self):
        assert _sort_sources([]) == []

    def test_generator_input(self):
        def gen():
            yield "zap"
            yield "nmap"

        assert _sort_sources(gen()) == ["nmap", "zap"]


# section build_asset_summary

class TestBuildAssetSummary:
    def test_groups_findings_by_asset_ref(self):
        findings = [
            {
                "target": "https://example.com/",
                "severity": "high",
                "confidence": 0.9,
                "finding_group_id": "group-1",
            },
            {
                "target": "https://example.com/",
                "severity": "medium",
                "confidence": 0.7,
                "finding_group_id": "group-2",
            },
            {
                "target": "https://other.com/",
                "severity": "low",
                "confidence": 0.5,
                "finding_group_id": "group-3",
            },
        ]
        summary = build_asset_summary(findings, [])
        assert len(summary) == 2
        labels = [item["label"] for item in summary]
        assert "https://example.com/" in labels
        assert "https://other.com/" in labels

    def test_highest_severity_wins(self):
        findings = [
            {"target": "https://x.com/", "severity": "low", "confidence": 0.5, "finding_group_id": "g1"},
            {"target": "https://x.com/", "severity": "critical", "confidence": 0.8, "finding_group_id": "g2"},
        ]
        summary = build_asset_summary(findings, [])
        assert summary[0]["highest_severity"] == "critical"

    def test_empty_list(self):
        assert build_asset_summary([], []) == []

    def test_finding_count_accumulated(self):
        findings = [
            {"target": "https://x.com/", "severity": "low", "confidence": 0.4, "finding_group_id": "g1"},
            {"target": "https://x.com/", "severity": "low", "confidence": 0.8, "finding_group_id": "g2"},
        ]
        summary = build_asset_summary(findings, [])
        assert summary[0]["finding_count"] == 2


# section existing tests preserved

def test_build_finding_groups_merges_duplicate_group_ids():
    findings = [
        {
            "id": "finding-1",
            "finding_group_id": "group:web:csp",
            "title": "Missing Content-Security-Policy",
            "severity": "medium",
            "category": "Transport Security",
            "target": "https://example.com",
            "occurrence_count": 2,
            "confidence": 0.82,
            "corroborating_sources": ["crawl"],
        },
        {
            "id": "finding-2",
            "finding_group_id": "group:web:csp",
            "title": "Missing Content-Security-Policy",
            "severity": "medium",
            "category": "Transport Security",
            "target": "https://example.com",
            "occurrence_count": 3,
            "confidence": 0.84,
            "corroborating_sources": ["nuclei"],
        },
    ]
    groups = build_finding_groups(findings)
    assert len(groups) == 1
    assert groups[0]["occurrence_count"] == 3
    assert set(groups[0]["corroborating_sources"]) == {"crawl", "nuclei"}
    assert len(groups[0]["findings"]) == 2


def test_build_scan_diff_tracks_new_resolved_and_changed_groups():
    current = [
        {"id": "new-1", "finding_group_id": "group:new", "title": "New finding", "severity": "high", "confidence": 0.9, "validated": False},
        {"id": "chg-2", "finding_group_id": "group:changed", "title": "Changed finding", "severity": "medium", "confidence": 0.8, "validated": True},
    ]
    previous = [
        {"id": "old-1", "finding_group_id": "group:resolved", "title": "Resolved finding", "severity": "low", "confidence": 0.4, "validated": False},
        {"id": "chg-1", "finding_group_id": "group:changed", "title": "Changed finding", "severity": "low", "confidence": 0.3, "validated": False},
    ]
    diff = build_scan_diff(current, previous)
    assert diff["summary"] == {"new_count": 1, "resolved_count": 1, "changed_count": 1}
    assert diff["new"][0]["id"] == "group:new"
    assert diff["resolved"][0]["id"] == "group:resolved"
    assert diff["changed"][0]["group_id"] == "group:changed"

