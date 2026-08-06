import pytest
from fastapi import HTTPException

from backend.secuscan.routes import _validate_lengths


def test_valid_name_under_255_chars_passes():
    # Should not raise
    _validate_lengths(name="a" * 100)


def test_valid_description_and_notes_under_2000_chars_passes():
    # Should not raise
    _validate_lengths(description="d" * 500, notes="n" * 500)


def test_name_exactly_255_chars_passes():
    # Should not raise — boundary is inclusive
    _validate_lengths(name="a" * 255)


def test_name_over_255_chars_raises_with_detail_message():
    with pytest.raises(HTTPException) as exc_info:
        _validate_lengths(name="a" * 256)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Resource name exceeds maximum length of 255 characters"


def test_description_exactly_2000_chars_passes():
    # Should not raise — boundary is inclusive
    _validate_lengths(description="d" * 2000)


def test_description_over_2000_chars_raises_http_exception():
    with pytest.raises(HTTPException) as exc_info:
        _validate_lengths(description="d" * 2001)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Resource description exceeds maximum length of 2000 characters"


def test_notes_over_2000_chars_raises_http_exception():
    with pytest.raises(HTTPException) as exc_info:
        _validate_lengths(notes="n" * 2001)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Resource notes exceeds maximum length of 2000 characters"


def test_custom_resource_type_reflected_in_error_message():
    with pytest.raises(HTTPException) as exc_info:
        _validate_lengths(name="a" * 256, resource_type="Target policy")

    assert exc_info.value.detail == "Target policy name exceeds maximum length of 255 characters"


def test_none_values_for_optional_fields_pass():
    # All fields default to None — should not raise
    _validate_lengths()
    _validate_lengths(name=None, description=None, notes=None)