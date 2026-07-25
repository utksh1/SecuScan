"""
Unit tests for executor.py module-level helpers:
  - _row_value: dict/sqlite row accessor with default
  - _validate_risk_fields: validates exploitability, confidence, asset_exposure bounds

Imports the real production functions so regressions are caught.
"""

import pytest

from backend.secuscan.executor import _row_value, _validate_risk_fields


class TestRowValue:
    """Tests for _row_value."""

    def test_dict_key_present(self):
        """Returns the value when the key exists in the dict."""
        assert _row_value({"a": 1}, "a") == 1

    def test_dict_key_missing_returns_none(self):
        """Returns None when the key is absent and no default is given."""
        assert _row_value({"a": 1}, "b") is None

    def test_dict_key_missing_with_default(self):
        """Returns the default when the key is absent."""
        assert _row_value({"a": 1}, "b", "fallback") == "fallback"

    def test_none_row_returns_default(self):
        """None row returns the default (handles sqlite NULL gracefully)."""
        assert _row_value(None, "a") is None
        assert _row_value(None, "a", "fallback") == "fallback"

    def test_empty_dict_returns_default(self):
        """Empty dict returns the default for missing keys."""
        assert _row_value({}, "a") is None
        assert _row_value({}, "a", "fallback") == "fallback"

    def test_string_value_returned(self):
        """String values are returned correctly."""
        assert _row_value({"k": "hello"}, "k") == "hello"

    def test_zero_and_false_are_valid_values(self):
        """Zero and False are returned as-is (not treated as missing)."""
        assert _row_value({"zero": 0, "false": False}, "zero") == 0
        assert _row_value({"zero": 0, "false": False}, "false") is False


class TestValidateRiskFieldsExploitability:
    """Tests for _validate_risk_fields — exploitability field."""

    def test_valid_exploitability_integer(self):
        """Integer exploitability in [0, 10] is accepted."""
        _validate_risk_fields({"exploitability": 5})
        _validate_risk_fields({"exploitability": 0})
        _validate_risk_fields({"exploitability": 10})

    def test_valid_exploitability_float(self):
        """Float exploitability in [0, 10] is accepted."""
        _validate_risk_fields({"exploitability": 5.5})

    def test_exploitability_none_is_ignored(self):
        """None exploitability is accepted (field is optional)."""
        _validate_risk_fields({"exploitability": None})

    def test_exploitability_missing_is_ignored(self):
        """Missing exploitability is accepted."""
        _validate_risk_fields({})

    def test_exploitability_below_zero_rejected(self):
        """Negative exploitability raises ValueError."""
        with pytest.raises(ValueError, match="exploitability"):
            _validate_risk_fields({"exploitability": -1})

    def test_exploitability_above_ten_rejected(self):
        """Exploitability > 10 raises ValueError."""
        with pytest.raises(ValueError, match="exploitability"):
            _validate_risk_fields({"exploitability": 11})

    def test_exploitability_string_rejected(self):
        """String exploitability raises ValueError."""
        with pytest.raises(ValueError, match="exploitability must be numeric"):
            _validate_risk_fields({"exploitability": "high"})


class TestValidateRiskFieldsConfidence:
    """Tests for _validate_risk_fields — confidence field."""

    def test_valid_confidence(self):
        """Confidence in [0, 1] is accepted."""
        _validate_risk_fields({"confidence": 0.5})
        _validate_risk_fields({"confidence": 0})
        _validate_risk_fields({"confidence": 1})

    def test_confidence_none_ignored(self):
        """None confidence is accepted."""
        _validate_risk_fields({"confidence": None})

    def test_confidence_below_zero_rejected(self):
        """Negative confidence raises ValueError."""
        with pytest.raises(ValueError, match="confidence"):
            _validate_risk_fields({"confidence": -0.1})

    def test_confidence_above_one_rejected(self):
        """Confidence > 1 raises ValueError."""
        with pytest.raises(ValueError, match="confidence"):
            _validate_risk_fields({"confidence": 1.1})

    def test_confidence_string_rejected(self):
        """String confidence raises ValueError."""
        with pytest.raises(ValueError, match="confidence must be numeric"):
            _validate_risk_fields({"confidence": "high"})


class TestValidateRiskFieldsAssetExposure:
    """Tests for _validate_risk_fields — asset_exposure field."""

    def test_valid_asset_exposure_values(self):
        """Valid asset_exposure values are accepted (case-insensitive)."""
        for val in ("critical", "high", "medium", "low",
                    "CRITICAL", "High", "Medium", "Low"):
            _validate_risk_fields({"asset_exposure": val})

    def test_asset_exposure_none_ignored(self):
        """None asset_exposure is accepted."""
        _validate_risk_fields({"asset_exposure": None})

    def test_asset_exposure_missing_ignored(self):
        """Missing asset_exposure is accepted."""
        _validate_risk_fields({})

    def test_asset_exposure_invalid_value_rejected(self):
        """Invalid asset_exposure raises ValueError."""
        with pytest.raises(ValueError, match="asset_exposure must be one of"):
            _validate_risk_fields({"asset_exposure": "unknown"})

    def test_asset_exposure_non_string_rejected(self):
        """Non-string asset_exposure (e.g., int) raises ValueError, not AttributeError."""
        with pytest.raises(ValueError, match="asset_exposure must be a string"):
            _validate_risk_fields({"asset_exposure": 123})

    def test_asset_exposure_boolean_rejected(self):
        """Boolean asset_exposure raises ValueError."""
        with pytest.raises(ValueError, match="asset_exposure must be a string"):
            _validate_risk_fields({"asset_exposure": True})

    def test_asset_exposure_empty_string_rejected(self):
        """Empty string asset_exposure raises ValueError."""
        with pytest.raises(ValueError, match="asset_exposure must be one of"):
            _validate_risk_fields({"asset_exposure": ""})
