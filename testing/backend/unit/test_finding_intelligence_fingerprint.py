import sys

sys.path.insert(0, ".")

from backend.secuscan.finding_intelligence import (
    _fingerprint_score,
    _finding_kind_for,
    _typed_evidence,
)


class TestFingerprintScore:
    def test_validated_yields_full_score(self):
        finding = {"validated": True, "metadata": {}}
        score, strength = _fingerprint_score(finding)
        assert score == 1.0
        assert strength == "validated"

    def test_exact_match(self):
        finding = {"metadata": {"match_strength": "exact"}}
        score, strength = _fingerprint_score(finding)
        assert score == 0.95
        assert strength == "exact"

    def test_strong_fuzzy(self):
        finding = {"metadata": {"match_strength": "strong_fuzzy"}}
        score, strength = _fingerprint_score(finding)
        assert score == 0.8
        assert strength == "strong_fuzzy"

    def test_fuzzy(self):
        finding = {"metadata": {"match_strength": "fuzzy"}}
        score, strength = _fingerprint_score(finding)
        assert score == 0.7
        assert strength == "fuzzy"

    def test_family(self):
        finding = {"metadata": {"match_strength": "family"}}
        score, strength = _fingerprint_score(finding)
        assert score == 0.45
        assert strength == "family"

    def test_none_yields_default(self):
        finding = {"metadata": {"match_strength": "none"}}
        score, strength = _fingerprint_score(finding)
        assert score == 0.25
        assert strength == "none"

    def test_missing_metadata_defaults(self):
        finding = {}
        score, strength = _fingerprint_score(finding)
        assert score == 0.25
        assert strength == "none"

    def test_unknown_strength_defaults(self):
        finding = {"metadata": {"match_strength": "unknown_strength"}}
        score, strength = _fingerprint_score(finding)
        assert score == 0.0
        assert strength == "unknown_strength"


class TestFindingKindFor:
    def test_validated_high_severity_is_validated_issue(self):
        finding = {"validated": True, "severity": "high", "category": "unknown"}
        assert _finding_kind_for(finding) == "validated_issue"

    def test_observation_category_is_observation(self):
        finding = {"category": "attack surface", "severity": "info"}
        assert _finding_kind_for(finding) == "observation"

    def test_high_severity_is_suspected_issue(self):
        finding = {"category": "unknown", "severity": "high"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_cve_is_suspected_issue(self):
        finding = {"category": "info", "severity": "info", "cve": "CVE-2024-1"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_cpe_correlation_is_suspected_issue(self):
        finding = {
            "category": "info",
            "severity": "info",
            "validation_method": "cpe_cve_correlation",
        }
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_low_severity_no_cve_is_observation(self):
        finding = {"category": "unknown", "severity": "low"}
        assert _finding_kind_for(finding) == "observation"

    def test_empty_category_defaults_to_observation(self):
        finding = {"category": "", "severity": "info"}
        assert _finding_kind_for(finding) == "observation"


class TestTypedEvidence:
    def test_dict_item_returns_structured_evidence(self):
        item = {
            "type": "http_response",
            "label": "HTTP Header",
            "value": "X-Frame-Options: DENY",
            "artifact_ref": "ref-1",
            "source": "scanner",
            "observed_at": "2024-01-01T00:00:00Z",
            "confidence": 0.95,
        }
        result = _typed_evidence(item, source="base", observed_at="2024-01-01T00:00:00Z", confidence=0.8)
        assert result["type"] == "http_response"
        assert result["label"] == "HTTP Header"
        assert result["value"] == "X-Frame-Options: DENY"
        assert result["artifact_ref"] == "ref-1"
        assert result["confidence"] == 0.95

    def test_non_dict_item_returns_default_evidence(self):
        result = _typed_evidence("some text", source="scanner", observed_at="t", confidence=0.75)
        assert result["type"] == "evidence"
        assert result["label"] == "Evidence"
        assert result["value"] == "some text"
        assert result["source"] == "scanner"
        assert result["confidence"] == 0.75

    def test_clamps_confidence_between_zero_and_one(self):
        item = {"confidence": 1.5}
        result = _typed_evidence(item, source="s", observed_at="t", confidence=0.5)
        assert result["confidence"] == 1.0

    def test_uses_base_confidence_when_item_has_none(self):
        item = {}
        result = _typed_evidence(item, source="s", observed_at="t", confidence=0.9)
        assert result["confidence"] == 0.9

    def test_observed_at_defaults_to_provided(self):
        item = {}
        result = _typed_evidence(item, source="s", observed_at="2024-06-01T00:00:00Z", confidence=0.5)
        assert result["observed_at"] == "2024-06-01T00:00:00Z"

    def test_missing_label_uses_title_cased_type(self):
        item = {"type": "http_header"}
        result = _typed_evidence(item, source="s", observed_at="t", confidence=0.5)
        assert result["label"] == "Http Header"
