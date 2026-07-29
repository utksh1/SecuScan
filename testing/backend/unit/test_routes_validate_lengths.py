"""
Unit tests for backend.secuscan.routes_validation_helpers._validate_lengths.

Run with:
    python3 -m pytest testing/backend/unit/test_routes_validate_lengths.py -v --noconftest
"""

from __future__ import annotations

import pytest
from starlette.exceptions import HTTPException

from backend.secuscan.routes_validation_helpers import _validate_lengths


class TestValidateLengths:
    def test_valid_name_under_255_chars_passes(self):
        _validate_lengths(name="A" * 255)

    def test_name_exactly_255_chars_passes(self):
        _validate_lengths(name="A" * 255)

    def test_name_over_255_chars_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_lengths(name="A" * 256)
        assert exc_info.value.status_code == 400
        assert "255" in exc_info.value.detail

    def test_valid_description_under_2000_chars_passes(self):
        _validate_lengths(description="B" * 2000)

    def test_description_exactly_2000_chars_passes(self):
        _validate_lengths(description="B" * 2000)

    def test_description_over_2000_chars_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_lengths(description="B" * 2001)
        assert exc_info.value.status_code == 400
        assert "2000" in exc_info.value.detail

    def test_notes_over_2000_chars_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_lengths(notes="C" * 2001)
        assert exc_info.value.status_code == 400
        assert "2000" in exc_info.value.detail

    def test_custom_resource_type_in_error_message(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_lengths(name="X" * 300, resource_type="CustomPolicy")
        assert "CustomPolicy" in exc_info.value.detail

    def test_none_values_pass(self):
        # None means field not provided; should pass
        _validate_lengths(name=None, description=None, notes=None)

    def test_whitespace_only_still_counted(self):
        # str("  ") = "  " which has len=2, so should pass
        _validate_lengths(name="  ")

    def test_all_fields_valid_together(self):
        _validate_lengths(
            name="Valid Name",
            description="Valid description up to 2000 chars",
            notes="Valid notes up to 2000 chars",
        )
