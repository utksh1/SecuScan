"""
Regression tests for unknown and missing severity fallback — Issue #2165.

Verifies that compute_risk_score and compute_risk_factors return a safe,
controlled, documented result whenever the severity parameter is:

  - an unrecognised label   (e.g. "extreme", "SEVERE", "n/a")
  - an empty string         ("")
  - a whitespace-only string
  - None / a non-string type (defensive contract)
  - a numeric string        ("5", "10")
  - a mixed-case variant    ("CRITICAL", "High")

All of the above exercised against SEVERITY_MAP directly via _severity_score,
and end-to-end through compute_risk_score and compute_risk_factors.

Acceptance criteria (from issue):
  1. The regression case is reproducible in an automated test.
  2. The expected safe behaviour is asserted explicitly (score in [0,10],
     detail is a non-empty string, factor shape is canonical).
  3. Existing behaviour remains covered.
  4. The focused test passes locally.
"""

from datetime import datetime, timezone

import pytest

from backend.secuscan.risk_scoring import (
    SEVERITY_MAP,
    WEIGHTS,
    _severity_score,
    compute_risk_factors,
    compute_risk_score,
)

# ---------------------------------------------------------------------------
# Constants used in assertions
# ---------------------------------------------------------------------------

# The documented fallback raw score for any unrecognised severity
FALLBACK_SEVERITY_SCORE: float = 0.5

# Canonical factor keys every call must return
CANONICAL_FACTOR_KEYS = {"severity", "exploitability", "asset_exposure", "recency", "confidence"}

# Required keys on every factor dict
REQUIRED_FACTOR_FIELDS = {"factor", "label", "value", "score", "weight", "contribution", "detail"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_score_in_range(score: float, label: str = "") -> None:
    assert isinstance(score, float), f"Score must be float, got {type(score)} [{label}]"
    assert 0.0 <= score <= 10.0, f"Score {score} out of [0,10] [{label}]"


def _assert_factors_shape(factors: list, sev_label: str = "") -> None:
    assert len(factors) == 5, f"Expected 5 factors, got {len(factors)} [{sev_label}]"
    factor_names = {f["factor"] for f in factors}
    assert (
        factor_names == CANONICAL_FACTOR_KEYS
    ), f"Factor keys mismatch: {factor_names} [{sev_label}]"
    for f in factors:
        missing = REQUIRED_FACTOR_FIELDS - set(f.keys())
        assert not missing, f"Factor '{f['factor']}' missing keys {missing} [{sev_label}]"
        assert (
            isinstance(f["detail"], str) and f["detail"]
        ), f"Factor '{f['factor']}' has empty/non-string detail [{sev_label}]"
        _assert_score_in_range(f["score"], f"factor={f['factor']}, sev={sev_label}")


# ===========================================================================
# 1.  _severity_score — the raw lookup layer
# ===========================================================================


class TestSeverityScoreFallback:
    """_severity_score must return FALLBACK_SEVERITY_SCORE (0.5) for unknown inputs."""

    # ---- unrecognised labels -----------------------------------------------

    @pytest.mark.parametrize(
        "label",
        [
            "extreme",
            "SEVERE",
            "urgent",
            "n/a",
            "none",
            "unknown",
            "warning",
            "catastrophic",
            "negligible",
            "trace",
            "verbose",
            "debug",
            "0",  # numeric-ish strings not in map
            "99",
            "10.0",
        ],
    )
    def test_unrecognised_label_returns_fallback(self, label: str) -> None:
        """Any label not in SEVERITY_MAP must fall back to 0.5."""
        result = _severity_score(label)
        assert (
            result == FALLBACK_SEVERITY_SCORE
        ), f"_severity_score({label!r}) returned {result}, expected {FALLBACK_SEVERITY_SCORE}"

    # ---- empty / whitespace -------------------------------------------------

    def test_empty_string_returns_fallback(self) -> None:
        assert _severity_score("") == FALLBACK_SEVERITY_SCORE

    def test_whitespace_only_returns_fallback(self) -> None:
        # "   ".lower() → "   ", not in map → fallback
        assert _severity_score("   ") == FALLBACK_SEVERITY_SCORE

    # ---- case-insensitivity for known labels --------------------------------

    @pytest.mark.parametrize(
        "label,expected",
        [
            ("CRITICAL", 10.0),
            ("Critical", 10.0),
            ("HIGH", 7.5),
            ("High", 7.5),
            ("MEDIUM", 5.0),
            ("Medium", 5.0),
            ("LOW", 2.5),
            ("Low", 2.5),
            ("INFO", 0.5),
            ("Info", 0.5),
        ],
    )
    def test_known_labels_case_insensitive(self, label: str, expected: float) -> None:
        """All known severity labels must be recognised regardless of case."""
        assert _severity_score(label) == expected

    # ---- SEVERITY_MAP completeness -----------------------------------------

    def test_severity_map_covers_all_known_labels(self) -> None:
        """SEVERITY_MAP must contain exactly the five documented levels."""
        expected_keys = {"critical", "high", "medium", "low", "info"}
        assert (
            set(SEVERITY_MAP.keys()) == expected_keys
        ), f"SEVERITY_MAP keys changed: {set(SEVERITY_MAP.keys())}"

    def test_fallback_value_is_documented(self) -> None:
        """The fallback value 0.5 is the same as 'info' — confirming intentional safe default."""
        assert (
            FALLBACK_SEVERITY_SCORE == SEVERITY_MAP["info"]
        ), "Fallback value must equal the 'info' score; update FALLBACK_SEVERITY_SCORE if changed."


# ===========================================================================
# 2.  compute_risk_score — end-to-end score with unknown severity
# ===========================================================================


class TestComputeRiskScoreUnknownSeverity:
    """compute_risk_score must return a valid float in [0,10] for any severity string."""

    @pytest.mark.parametrize(
        "bad_severity",
        [
            "extreme",
            "SEVERE",
            "urgent",
            "n/a",
            "unknown",
            "",
            "   ",
            "99",
            "critical!",  # trailing punctuation
            "high severity",  # spaces inside
        ],
    )
    def test_unknown_severity_score_in_range(self, bad_severity: str) -> None:
        """Unknown severity must always produce a score in [0, 10]."""
        score = compute_risk_score(bad_severity)
        _assert_score_in_range(score, label=bad_severity)

    def test_unknown_severity_uses_fallback_contribution(self) -> None:
        """
        When severity is unknown, the severity sub-score is 0.5 (fallback).
        This means with all other params at zero/default the score is
        deterministically computable.
        """
        # Severity contribution = 0.5 * 0.30 = 0.15
        # exploitability = 0.0 * 0.25 = 0.0
        # asset_exposure = None → 0.0 * 0.20 = 0.0
        # recency = None → 5.0 * 0.15 = 0.75
        # confidence = None → 0.0 * 0.10 = 0.0
        # total = 0.90 → rounded to 0.9
        expected = round(
            FALLBACK_SEVERITY_SCORE * WEIGHTS["severity"]
            + 0.0 * WEIGHTS["exploitability"]
            + 0.0 * WEIGHTS["asset_exposure"]
            + 5.0 * WEIGHTS["recency"]
            + 0.0 * WEIGHTS["confidence"],
            1,
        )
        score = compute_risk_score(
            "extreme",
            exploitability=None,
            asset_exposure=None,
            discovered_at=None,
            confidence=None,
        )
        assert (
            score == expected
        ), f"Expected {expected} for unknown severity with all defaults, got {score}"

    def test_unknown_severity_score_lower_than_low(self) -> None:
        """An unknown severity must score no higher than 'low' in normal conditions."""
        unknown_score = compute_risk_score("extreme", exploitability=5.0, asset_exposure="medium")
        low_score = compute_risk_score("low", exploitability=5.0, asset_exposure="medium")
        assert (
            unknown_score <= low_score
        ), f"Unknown severity score {unknown_score} should be <= low {low_score}"

    def test_unknown_severity_score_lower_than_info(self) -> None:
        """
        With the same other parameters, unknown severity equals 'info' (both map to 0.5).
        """
        unknown_score = compute_risk_score("mystery_level")
        info_score = compute_risk_score("info")
        assert (
            unknown_score == info_score
        ), f"Unknown severity {unknown_score} should equal info {info_score} — same fallback"

    def test_score_deterministic_for_same_unknown_severity(self) -> None:
        """Same unknown severity always produces the same score."""
        s1 = compute_risk_score(
            "extreme", exploitability=3.0, asset_exposure="high", confidence=0.5
        )
        s2 = compute_risk_score(
            "extreme", exploitability=3.0, asset_exposure="high", confidence=0.5
        )
        assert s1 == s2

    def test_score_still_valid_with_context_on_unknown_severity(self) -> None:
        """Context modifiers (exposure/criticality) are applied even with unknown severity."""
        score_no_ctx = compute_risk_score("extreme")
        score_public = compute_risk_score("extreme", exposure_context="public")
        score_private = compute_risk_score("extreme", exposure_context="private")
        # All must be in range
        _assert_score_in_range(score_no_ctx, "extreme/no-ctx")
        _assert_score_in_range(score_public, "extreme/public")
        _assert_score_in_range(score_private, "extreme/private")
        # Public should be higher than private (multiplier applies to fallback too)
        assert (
            score_public > score_private
        ), "Public exposure context should raise score even for unknown severity"

    @pytest.mark.parametrize(
        "bad_severity",
        ["", "   ", "extreme", "SEVERE", "n/a", "unknown"],
    )
    def test_score_always_rounded_to_one_decimal(self, bad_severity: str) -> None:
        """Score must always be rounded to 1 decimal place."""
        score = compute_risk_score(bad_severity)
        assert score == round(score, 1), f"Score {score} not rounded to 1dp for {bad_severity!r}"


# ===========================================================================
# 3.  compute_risk_factors — explanation shape for unknown severity
# ===========================================================================


class TestComputeRiskFactorsUnknownSeverity:
    """compute_risk_factors must return the canonical 5-factor list for any severity."""

    @pytest.mark.parametrize(
        "bad_severity",
        [
            "extreme",
            "SEVERE",
            "urgent",
            "n/a",
            "unknown",
            "",
        ],
    )
    def test_returns_five_canonical_factors(self, bad_severity: str) -> None:
        """Five factors with all required fields returned for unknown severity."""
        factors = compute_risk_factors(bad_severity)
        _assert_factors_shape(factors, sev_label=bad_severity)

    def test_severity_factor_value_preserves_original_label(self) -> None:
        """The 'value' field on the severity factor must echo back the original severity string."""
        original = "UNKNOWN_LEVEL"
        factors = compute_risk_factors(original)
        sev_factor = next(f for f in factors if f["factor"] == "severity")
        assert (
            sev_factor["value"] == original
        ), f"severity factor 'value' should be {original!r}, got {sev_factor['value']!r}"

    def test_severity_factor_score_is_fallback(self) -> None:
        """Severity factor score must be the fallback (0.5) for unknown label."""
        factors = compute_risk_factors("extreme")
        sev_factor = next(f for f in factors if f["factor"] == "severity")
        # base_severity=0.5, no context → sv=0.5
        assert (
            sev_factor["score"] == 0.5
        ), f"Expected severity factor score 0.5, got {sev_factor['score']}"

    def test_severity_factor_detail_is_nonempty_string(self) -> None:
        """Even for unknown severity, the detail explanation must be a non-empty string."""
        for bad in ("extreme", "", "n/a", "UNKNOWN"):
            factors = compute_risk_factors(bad)
            sev_factor = next(f for f in factors if f["factor"] == "severity")
            assert (
                isinstance(sev_factor["detail"], str) and sev_factor["detail"]
            ), f"detail must be non-empty string for severity={bad!r}"

    def test_severity_factor_contribution_matches_score_times_weight(self) -> None:
        """Factor contribution = score × weight (within rounding tolerance)."""
        factors = compute_risk_factors("extreme")
        sev_factor = next(f for f in factors if f["factor"] == "severity")
        expected_contribution = round(sev_factor["score"] * WEIGHTS["severity"], 2)
        assert (
            abs(sev_factor["contribution"] - expected_contribution) < 0.005
        ), f"contribution {sev_factor['contribution']} ≠ score×weight {expected_contribution}"

    def test_total_contributions_sum_close_to_factors_internal_score(self) -> None:
        """
        Sum of all factor contributions should be internally consistent within
        compute_risk_factors.

        Note: compute_risk_factors uses different internal defaults than
        compute_risk_score (e.g. exploitability defaults to 5.0 in factors vs
        0.0 in score).  We pass explicit values to control both paths equally.
        """
        bad_sev = "extreme"
        # Use explicit values so both functions see the same inputs
        kwargs = dict(
            exploitability=5.0,
            asset_exposure="medium",
            confidence=0.5,
        )
        risk_score = compute_risk_score(bad_sev, **kwargs)
        factors = compute_risk_factors(bad_sev, risk_score=risk_score, **kwargs)
        total = sum(f["contribution"] for f in factors)
        assert (
            abs(total - risk_score) < 0.1
        ), f"Contributions sum {total:.3f} deviates from risk_score {risk_score} by more than 0.1"

    def test_context_still_adjusts_severity_factor_for_unknown_sev(self) -> None:
        """Exposure context should still be reflected in the severity factor detail."""
        factors = compute_risk_factors(
            "extreme", exposure_context="public", business_criticality="critical"
        )
        sev_factor = next(f for f in factors if f["factor"] == "severity")
        # exposure_context and business_criticality must be surfaced
        assert (
            sev_factor.get("exposure_context") == "public"
        ), "exposure_context missing from severity factor"
        assert (
            sev_factor.get("business_criticality") == "critical"
        ), "business_criticality missing from severity factor"
        # Multiplier should be > 1 (public=1.5 × critical=1.5)
        assert (
            sev_factor.get("context_multiplier", 1.0) > 1.0
        ), "context_multiplier should exceed 1.0 for public+critical"

    def test_all_other_factors_unaffected_by_unknown_severity(self) -> None:
        """Exploitability, asset_exposure, recency, confidence factors behave normally."""
        factors = compute_risk_factors(
            "extreme",
            exploitability=7.0,
            asset_exposure="high",
            confidence=0.8,
            discovered_at=datetime.now(timezone.utc),
        )
        factor_map = {f["factor"]: f for f in factors}

        # Exploitability: 7.0 passed in explicitly
        assert factor_map["exploitability"]["score"] == 7.0

        # Asset exposure: "high" → 7.5
        assert factor_map["asset_exposure"]["score"] == 7.5

        # Recency: today → 10.0
        assert factor_map["recency"]["score"] == 10.0

        # Confidence: 0.8 → 8.0
        assert factor_map["confidence"]["score"] == 8.0


# ===========================================================================
# 4.  Missing severity (None / wrong type) — defensive contract
# ===========================================================================


class TestMissingSeverityDefensiveContract:
    """
    compute_risk_score and compute_risk_factors should never raise an unhandled
    exception even when called with None or a non-string severity.

    Note: the public API signature is str, so these are defensive guardrail
    tests. If the function raises, we document WHAT it raises so regressions
    are caught.
    """

    @pytest.mark.parametrize("bad_type", [None, 0, 42, 3.14, [], {}, True])
    def test_non_string_severity_raises_or_returns_safe(self, bad_type) -> None:
        """
        Non-string severity either returns a safe score or raises AttributeError/TypeError.
        Either outcome is acceptable — what is NOT acceptable is a silent wrong result
        or a crash that propagates further up the call stack as an unrelated error.
        """
        try:
            score = compute_risk_score(bad_type)  # type: ignore[arg-type]
            # If it doesn't raise, it must still produce a valid score
            _assert_score_in_range(score, label=str(bad_type))
        except (AttributeError, TypeError):
            # Expected — non-string types call .lower() which raises AttributeError
            pass

    @pytest.mark.parametrize("bad_type", [None, 0, 42])
    def test_non_string_severity_factors_raises_or_returns_safe(self, bad_type) -> None:
        """Same defensive contract for compute_risk_factors."""
        try:
            factors = compute_risk_factors(bad_type)  # type: ignore[arg-type]
            _assert_factors_shape(factors, sev_label=str(bad_type))
        except (AttributeError, TypeError):
            pass


# ===========================================================================
# 5.  Documented safe score table — regression pin
# ===========================================================================


class TestDocumentedSafeScoreTable:
    """
    Pin the exact fallback score produced for each unknown severity with all
    other parameters at their defaults.  Any change here is a breaking change
    that needs explicit review.

    Defaults used:
        exploitability=None  → 0.0   (weight 0.25)
        asset_exposure=None  → 0.0   (weight 0.20)
        discovered_at=None   → 5.0   (weight 0.15)
        confidence=None      → 0.0   (weight 0.10)
        severity unknown     → 0.5   (weight 0.30)

    Expected score = 0.5×0.30 + 0×0.25 + 0×0.20 + 5×0.15 + 0×0.10
                   = 0.15 + 0 + 0 + 0.75 + 0
                   = 0.90  →  rounds to 0.9
    """

    EXPECTED_FALLBACK_SCORE = 0.9

    @pytest.mark.parametrize(
        "unknown_severity",
        [
            "extreme",
            "SEVERE",
            "urgent",
            "n/a",
            "unknown",
            "gibberish",
            "!@#$%",
        ],
    )
    def test_unknown_severity_default_score_pinned(self, unknown_severity: str) -> None:
        """All unknown severities with all-default other params must produce 0.9."""
        score = compute_risk_score(
            unknown_severity,
            exploitability=None,
            asset_exposure=None,
            discovered_at=None,
            confidence=None,
        )
        assert score == self.EXPECTED_FALLBACK_SCORE, (
            f"Unknown severity {unknown_severity!r} produced score {score}, "
            f"expected pinned fallback {self.EXPECTED_FALLBACK_SCORE}. "
            "If the scoring formula changed intentionally, update this pin."
        )

    def test_empty_string_severity_default_score_pinned(self) -> None:
        """Empty string severity also falls back to the same pinned score."""
        score = compute_risk_score(
            "",
            exploitability=None,
            asset_exposure=None,
            discovered_at=None,
            confidence=None,
        )
        assert (
            score == self.EXPECTED_FALLBACK_SCORE
        ), f"Empty string severity produced {score}, expected {self.EXPECTED_FALLBACK_SCORE}"

    def test_known_severities_above_fallback_with_same_defaults(self) -> None:
        """Every known severity label must produce a score >= the fallback score."""
        fallback = self.EXPECTED_FALLBACK_SCORE
        for known in ("critical", "high", "medium", "low", "info"):
            score = compute_risk_score(
                known,
                exploitability=None,
                asset_exposure=None,
                discovered_at=None,
                confidence=None,
            )
            assert (
                score >= fallback
            ), f"Known severity '{known}' scored {score} which is below fallback {fallback}"
