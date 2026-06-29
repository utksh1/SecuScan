"""Tests for the risk scoring module."""

import json
import pytest
from datetime import datetime, timezone, timedelta
from backend.secuscan.risk_scoring import (
    compute_risk_score,
    compute_risk_factors,
)


class TestComputeRiskScore:
    """Determinism, bounds, and edge cases for the composite score."""

    def test_deterministic(self):
        """Same inputs always produce the same score."""
        s1 = compute_risk_score("critical", exploitability=9.0, asset_exposure="critical", confidence=0.9)
        s2 = compute_risk_score("critical", exploitability=9.0, asset_exposure="critical", confidence=0.9)
        assert s1 == s2

    def test_score_range(self):
        """Score is always in [0, 10]."""
        for sev in ("critical", "high", "medium", "low", "info"):
            score = compute_risk_score(sev)
            assert 0.0 <= score <= 10.0, f"Score {score} out of range for {sev}"

    def test_critical_maximises_score(self):
        """All maximum inputs yield the highest score."""
        score = compute_risk_score(
            "critical",
            exploitability=10.0,
            asset_exposure="critical",
            confidence=1.0,
            discovered_at=datetime.now(timezone.utc),
        )
        assert score > 8.0

    def test_info_minimises_score(self):
        """All minimum inputs yield the lowest score."""
        score = compute_risk_score(
            "info",
            exploitability=0.0,
            asset_exposure="low",
            confidence=0.0,
            discovered_at=datetime.now(timezone.utc) - timedelta(days=1000),
        )
        assert score < 4.0

    def test_exploitability_default(self):
        """None exploitability defaults to 5.0."""
        s1 = compute_risk_score("medium", exploitability=None)
        s2 = compute_risk_score("medium", exploitability=5.0)
        assert s1 == s2

    def test_confidence_default(self):
        """None confidence defaults to 0.5."""
        s1 = compute_risk_score("medium", confidence=None)
        s2 = compute_risk_score("medium", confidence=0.5)
        assert s1 == s2

    def test_asset_exposure_default(self):
        """None asset_exposure defaults to 'medium'."""
        s1 = compute_risk_score("medium", asset_exposure=None)
        s2 = compute_risk_score("medium", asset_exposure="medium")
        assert s1 == s2

    def test_recency_recent(self):
        """Finding from today gets max recency contribution."""
        today = datetime.now(timezone.utc)
        score = compute_risk_score("high", discovered_at=today)
        recent_score = compute_risk_score("high", discovered_at=today - timedelta(days=365))
        # Today should be higher than a year ago
        assert score > recent_score

    def test_recency_old(self):
        """Finding from >1 year ago gets minimum recency."""
        old = datetime.now(timezone.utc) - timedelta(days=400)
        score = compute_risk_score("high", discovered_at=old)
        old_score = compute_risk_score("high", discovered_at=old - timedelta(days=1000))
        assert score == old_score  # both floored at 1.0

    def test_recency_none(self):
        """None discovered_at defaults to moderate recency (5.0)."""
        s1 = compute_risk_score("medium")
        s2 = compute_risk_score("medium", discovered_at=datetime.now(timezone.utc) - timedelta(days=89))
        assert s1 == s2

    def test_exploitability_clamping(self):
        """Exploitability outside [0,10] is clamped."""
        s1 = compute_risk_score("high", exploitability=-5.0)
        s2 = compute_risk_score("high", exploitability=15.0)
        s3 = compute_risk_score("high", exploitability=0.0)
        s4 = compute_risk_score("high", exploitability=10.0)
        assert s1 == s3
        assert s2 == s4


class TestComputeRiskFactors:
    """Risk factor explanations."""

    def test_returns_five_factors(self):
        """Five factors returned: severity, exploitability, asset_exposure, recency, confidence."""
        factors = compute_risk_factors("critical")
        assert len(factors) == 5
        keys = {f["factor"] for f in factors}
        assert keys == {"severity", "exploitability", "asset_exposure", "recency", "confidence"}

    def test_contributions_sum_to_score(self):
        """Sum of weighted contributions equals the risk score."""
        score = compute_risk_score("high", exploitability=7.0, asset_exposure="high", confidence=0.8)
        factors = compute_risk_factors("high", exploitability=7.0, asset_exposure="high", confidence=0.8, risk_score=score)
        total = sum(f["contribution"] for f in factors)
        # Rounding may cause 0.01 delta
        assert abs(total - score) < 0.1

    def test_negative_exploitability(self):
        """Negative exploitability is handled gracefully."""
        factors = compute_risk_factors("medium", exploitability=-1.0)
        exf = [f for f in factors if f["factor"] == "exploitability"][0]
        assert exf["score"] >= 0

    def test_risk_factors_provide_detail(self):
        """Each factor has a non-empty detail string."""
        factors = compute_risk_factors("critical", exploitability=9.0, asset_exposure="critical", confidence=0.95)
        for f in factors:
            assert f["detail"], f"Factor {f['factor']} missing detail"


class TestFindingModelWithRiskFields:
    """The Finding pydantic model accepts the new risk fields."""

    def test_finding_with_risk_fields(self):
        from backend.secuscan.models import Finding

        finding = Finding(
            title="SQL Injection",
            category="injection",
            severity="critical",
            target="app.example.com",
            description="Input not sanitized",
            exploitability=8.5,
            confidence=0.95,
            asset_exposure="critical",
            risk_score=8.7,
            risk_factors=[{"factor": "severity", "score": 10.0, "weight": 0.30, "contribution": 3.0}],
        )
        assert finding.exploitability == 8.5
        assert finding.confidence == 0.95
        assert finding.asset_exposure == "critical"
        assert finding.risk_score == 8.7
        assert len(finding.risk_factors) == 1

    def test_finding_without_risk_fields(self):
        """Risk fields default to None/empty — backward compatible."""
        from backend.secuscan.models import Finding

        finding = Finding(
            title="XSS",
            category="xss",
            severity="medium",
            target="web.example.com",
            description="XSS found",
        )
        assert finding.exploitability is None
        assert finding.confidence is None
        assert finding.asset_exposure is None
        assert finding.risk_score is None
        assert finding.risk_factors == []


class TestRiskFieldValidation:
    """Validation of exploitability, confidence, asset_exposure bounds."""

    def test_exploitability_negative_raises(self):
        from backend.secuscan.executor import _validate_risk_fields
        import pytest
        with pytest.raises(ValueError, match="exploitability must be in"):
            _validate_risk_fields({"exploitability": -1, "severity": "medium"})

    def test_exploitability_too_high_raises(self):
        from backend.secuscan.executor import _validate_risk_fields
        import pytest
        with pytest.raises(ValueError, match="exploitability must be in"):
            _validate_risk_fields({"exploitability": 11, "severity": "medium"})

    def test_exploitability_valid(self):
        from backend.secuscan.executor import _validate_risk_fields
        # Should not raise
        _validate_risk_fields({"exploitability": 5.0, "severity": "medium"})
        _validate_risk_fields({"exploitability": 0, "severity": "medium"})
        _validate_risk_fields({"exploitability": 10, "severity": "medium"})

    def test_confidence_negative_raises(self):
        from backend.secuscan.executor import _validate_risk_fields
        import pytest
        with pytest.raises(ValueError, match="confidence must be in"):
            _validate_risk_fields({"confidence": -0.1, "severity": "medium"})

    def test_confidence_too_high_raises(self):
        from backend.secuscan.executor import _validate_risk_fields
        import pytest
        with pytest.raises(ValueError, match="confidence must be in"):
            _validate_risk_fields({"confidence": 1.1, "severity": "medium"})

    def test_confidence_valid(self):
        from backend.secuscan.executor import _validate_risk_fields
        _validate_risk_fields({"confidence": 0.0, "severity": "medium"})
        _validate_risk_fields({"confidence": 0.5, "severity": "medium"})
        _validate_risk_fields({"confidence": 1.0, "severity": "medium"})

    def test_asset_exposure_invalid_raises(self):
        from backend.secuscan.executor import _validate_risk_fields
        import pytest
        with pytest.raises(ValueError, match="asset_exposure must be one of"):
            _validate_risk_fields({"asset_exposure": "extreme", "severity": "medium"})

    def test_asset_exposure_valid(self):
        from backend.secuscan.executor import _validate_risk_fields
        for val in ("critical", "high", "medium", "low"):
            _validate_risk_fields({"asset_exposure": val, "severity": "medium"})

    def test_non_numeric_exploitability_raises(self):
        from backend.secuscan.executor import _validate_risk_fields
        import pytest
        with pytest.raises(ValueError, match="exploitability must be numeric"):
            _validate_risk_fields({"exploitability": "high", "severity": "medium"})

    def test_non_numeric_confidence_raises(self):
        from backend.secuscan.executor import _validate_risk_fields
        import pytest
        with pytest.raises(ValueError, match="confidence must be numeric"):
            _validate_risk_fields({"confidence": "yes", "severity": "medium"})


class TestParseDiscoveredAt:
    """discovered_at is passed correctly to risk scoring."""

    def test_parse_discovered_at_string(self):
        from backend.secuscan.executor import _parse_discovered_at
        from datetime import datetime, timezone
        dt = _parse_discovered_at({"discovered_at": "2026-05-20T12:00:00"})
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 20

    def test_parse_discovered_at_datetime(self):
        from backend.secuscan.executor import _parse_discovered_at
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        dt = _parse_discovered_at({"discovered_at": now})
        assert dt == now

    def test_parse_discovered_at_missing_uses_now(self):
        from backend.secuscan.executor import _parse_discovered_at
        from datetime import datetime, timezone
        dt = _parse_discovered_at({})
        assert dt is not None
        now = datetime.now(timezone.utc)
        assert abs((now - dt).total_seconds()) < 5

    def test_parse_discovered_at_invalid_falls_back_to_now(self):
        from backend.secuscan.executor import _parse_discovered_at
        from datetime import datetime, timezone
        dt = _parse_discovered_at({"discovered_at": "not-a-date"})
        assert dt is not None
        now = datetime.now(timezone.utc)
        assert abs((now - dt).total_seconds()) < 5

    def test_recency_with_real_timestamp(self):
        """Score differs when a real discovered_at is passed vs None."""
        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone.utc)
        recent = compute_risk_score("high", discovered_at=today)
        old = compute_risk_score("high", discovered_at=today - timedelta(days=400))
        no_date = compute_risk_score("high")
        assert recent > no_date > old

    def test_risk_factors_with_real_timestamp(self):
        """Factor detail includes actual discovered_at."""
        from datetime import datetime, timezone
        factors = compute_risk_factors("medium", discovered_at=datetime(2026, 5, 20, tzinfo=timezone.utc))
        recency = [f for f in factors if f["factor"] == "recency"][0]
        assert "2026-05-20" in recency["value"]


class TestBackfillRiskScores:
    """Tests for backfilling risk scores on existing findings."""

    @pytest.mark.asyncio
    async def test_backfill_sets_risk_score_on_null_findings(self, setup_test_environment):
        """Findings with NULL risk_score get a computed score after backfill."""
        from backend.secuscan.config import settings
        from backend.secuscan.database import init_db, get_db

        await init_db(settings.database_path)
        db = await get_db()

        # Insert referenced task first to satisfy foreign key constraint
        await db.execute(
            "INSERT INTO tasks (id, plugin_id, tool_name, target) VALUES (?, ?, ?, ?)",
            ("task-1", "test", "test", "example.com")
        )

        finding_id = "test-finding-001"
        await db.execute(
            """
            INSERT INTO findings (
                id, task_id, plugin_id, title, category, severity,
                target, description, discovered_at,
                exploitability, confidence, asset_exposure,
                risk_score, risk_factors_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, '[]')
            """,
            (finding_id, "task-1", "test", "Test Finding", "test",
             "critical", "example.com", "XSS vulnerability",
             "2026-05-20T12:00:00", 8.0, 0.9, "critical"),
        )

        row = await db.fetchone("SELECT risk_score FROM findings WHERE id = ?", (finding_id,))
        assert row["risk_score"] is None

        await db._backfill_risk_scores()

        row = await db.fetchone(
            "SELECT risk_score, risk_factors_json FROM findings WHERE id = ?",
            (finding_id,),
        )
        assert row["risk_score"] is not None
        assert isinstance(row["risk_score"], (int, float))
        assert row["risk_score"] > 0
        factors = json.loads(row["risk_factors_json"])
        assert len(factors) == 5

    @pytest.mark.asyncio
    async def test_backfill_idempotent(self, setup_test_environment):
        """Backfill does not modify findings that already have a risk_score."""
        from backend.secuscan.config import settings
        from backend.secuscan.database import init_db, get_db

        await init_db(settings.database_path)
        db = await get_db()

        # Insert referenced task first to satisfy foreign key constraint
        await db.execute(
            "INSERT INTO tasks (id, plugin_id, tool_name, target) VALUES (?, ?, ?, ?)",
            ("task-2", "test", "test", "example.com")
        )

        finding_id = "test-finding-002"
        await db.execute(
            """
            INSERT INTO findings (
                id, task_id, plugin_id, title, category, severity,
                target, description, discovered_at, risk_score, risk_factors_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (finding_id, "task-2", "test", "Already Scored", "test",
             "high", "example.com", "Old finding",
             "2026-01-01T00:00:00", 5.0, '[{"factor":"severity","score":5}]'),
        )

        await db._backfill_risk_scores()

        row = await db.fetchone("SELECT risk_score FROM findings WHERE id = ?", (finding_id,))
        assert row["risk_score"] == 5.0
