"""Unit tests for _validate_risk_fields in backend/secuscan/executor.py."""

import pytest

from backend.secuscan.executor_helpers import _validate_risk_fields


class TestValidateRiskFields:
    def test_valid_exploitability_integer(self):
        finding = {"exploitability": 5}
        _validate_risk_fields(finding)  # must not raise

    def test_valid_exploitability_float(self):
        finding = {"exploitability": 7.5}
        _validate_risk_fields(finding)

    def test_valid_exploitability_boundary_values(self):
        _validate_risk_fields({"exploitability": 0})
        _validate_risk_fields({"exploitability": 10})

    def test_valid_exploitability_none(self):
        finding = {"exploitability": None}
        _validate_risk_fields(finding)

    def test_invalid_exploitability_negative(self):
        finding = {"exploitability": -1}
        with pytest.raises(ValueError, match="exploitability"):
            _validate_risk_fields(finding)

    def test_invalid_exploitability_too_high(self):
        finding = {"exploitability": 11}
        with pytest.raises(ValueError, match="exploitability"):
            _validate_risk_fields(finding)

    def test_invalid_exploitability_non_numeric(self):
        finding = {"exploitability": "high"}
        with pytest.raises(ValueError, match="exploitability.*numeric"):
            _validate_risk_fields(finding)

    def test_valid_confidence_zero(self):
        finding = {"confidence": 0}
        _validate_risk_fields(finding)

    def test_valid_confidence_half(self):
        finding = {"confidence": 0.5}
        _validate_risk_fields(finding)

    def test_valid_confidence_one(self):
        finding = {"confidence": 1.0}
        _validate_risk_fields(finding)

    def test_valid_confidence_none(self):
        finding = {"confidence": None}
        _validate_risk_fields(finding)

    def test_invalid_confidence_negative(self):
        finding = {"confidence": -0.1}
        with pytest.raises(ValueError, match="confidence"):
            _validate_risk_fields(finding)

    def test_invalid_confidence_too_high(self):
        finding = {"confidence": 1.5}
        with pytest.raises(ValueError, match="confidence"):
            _validate_risk_fields(finding)

    def test_invalid_confidence_non_numeric(self):
        finding = {"confidence": "0.8"}
        with pytest.raises(ValueError, match="confidence.*numeric"):
            _validate_risk_fields(finding)

    def test_valid_asset_exposure_critical(self):
        finding = {"asset_exposure": "critical"}
        _validate_risk_fields(finding)

    def test_valid_asset_exposure_high(self):
        finding = {"asset_exposure": "high"}
        _validate_risk_fields(finding)

    def test_valid_asset_exposure_medium(self):
        finding = {"asset_exposure": "medium"}
        _validate_risk_fields(finding)

    def test_valid_asset_exposure_low(self):
        finding = {"asset_exposure": "low"}
        _validate_risk_fields(finding)

    def test_valid_asset_exposure_none(self):
        finding = {"asset_exposure": None}
        _validate_risk_fields(finding)

    def test_invalid_asset_exposure(self):
        finding = {"asset_exposure": "unknown"}
        with pytest.raises(ValueError, match="asset_exposure"):
            _validate_risk_fields(finding)

    def test_all_valid_fields_passes(self):
        finding = {
            "exploitability": 7,
            "confidence": 0.8,
            "asset_exposure": "high",
        }
        _validate_risk_fields(finding)

    def test_empty_finding_passes(self):
        _validate_risk_fields({})

    def test_invalid_exploitability_blocks_confidence(self):
        finding = {"exploitability": -5, "confidence": 0.9}
        with pytest.raises(ValueError, match="exploitability"):
            _validate_risk_fields(finding)
