"""Unit tests for semver-to-PEP 440 helper functions.

Tests handle_caret, handle_tilde, and handle_wildcard helpers directly
to cover edge cases not exercised by the top-level semver_to_pep440 tests.
"""

import pytest
from backend.secuscan.remediation import handle_caret, handle_tilde, handle_wildcard


class TestHandleCaret:
    """Tests for handle_caret(ver_str) -> List[str]"""

    def test_caret_major_version(self):
        result = handle_caret("1.2.3")
        assert result == [">=1.2.3", "<2.0.0"]

    def test_caret_minor_version_nonzero(self):
        result = handle_caret("0.2.3")
        assert result == [">=0.2.3", "<0.3.0"]

    def test_caret_patch_version_nonzero(self):
        result = handle_caret("0.0.3")
        assert result == [">=0.0.3", "<0.0.4"]

    def test_caret_minor_zero_patch_nonzero(self):
        result = handle_caret("0.1.0")
        assert result == [">=0.1.0", "<0.2.0"]

    def test_caret_all_zero_except_patch(self):
        result = handle_caret("0.0.1")
        assert result == [">=0.0.1", "<0.0.2"]

    def test_caret_large_version(self):
        result = handle_caret("10.20.30")
        assert result == [">=10.20.30", "<11.0.0"]

    def test_caret_two_part_version(self):
        result = handle_caret("1.2")
        assert result == [">=1.2", "<2.0.0"]

    def test_caret_single_part_version(self):
        result = handle_caret("5")
        assert result == [">=5", "<6.0.0"]


class TestHandleTilde:
    """Tests for handle_tilde(ver_str) -> List[str]"""

    def test_tilde_three_part_version(self):
        result = handle_tilde("1.2.3")
        assert result == [">=1.2.3", "<1.3.0"]

    def test_tilde_two_part_version(self):
        result = handle_tilde("1.2")
        assert result == [">=1.2", "<1.3.0"]

    def test_tilde_single_part_version(self):
        result = handle_tilde("1")
        assert result == [">=1", "<2.0.0"]

    def test_tilde_major_zero(self):
        result = handle_tilde("0.5.2")
        assert result == [">=0.5.2", "<0.6.0"]

    def test_tilde_large_version(self):
        result = handle_tilde("10.20.30")
        assert result == [">=10.20.30", "<10.21.0"]


class TestHandleWildcard:
    """Tests for handle_wildcard(part: str) -> List[str]"""

    def test_wildcard_single_part(self):
        result = handle_wildcard("1")
        assert result == [">=1.0.0", "<2.0.0"]

    def test_wildcard_two_parts(self):
        result = handle_wildcard("1.2")
        assert result == [">=1.2.0", "<1.3.0"]

    def test_wildcard_three_parts_with_x(self):
        result = handle_wildcard("1.2.x")
        assert result == [">=1.2.0", "<1.3.0"]

    def test_wildcard_x_only(self):
        result = handle_wildcard("x")
        assert result == []

    def test_wildcard_star_only(self):
        result = handle_wildcard("*")
        assert result == []

    def test_wildcard_star_in_second_position(self):
        result = handle_wildcard("1.*")
        assert result == [">=1.0.0", "<2.0.0"]

    def test_wildcard_x_in_third_position(self):
        result = handle_wildcard("1.2.x")
        assert result == [">=1.2.0", "<1.3.0"]

    def test_wildcard_large_version(self):
        result = handle_wildcard("10.20")
        assert result == [">=10.20.0", "<10.21.0"]

    def test_wildcard_fully_qualified_returns_empty(self):
        result = handle_wildcard("1.2.3")
        assert result == []
