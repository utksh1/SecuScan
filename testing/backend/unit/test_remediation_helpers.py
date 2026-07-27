"""Tests for remediation.py internal helpers: handle_caret, handle_tilde, handle_wildcard."""

import pytest

from backend.secuscan.remediation import handle_caret, handle_tilde, handle_wildcard


class TestHandleCaret:
    """handle_caret must correctly translate npm-style caret ranges to PEP 440."""

    def test_caret_standard(self):
        assert handle_caret("1.2.3") == [">=1.2.3", "<2.0.0"]

    def test_caret_minor_above_zero(self):
        assert handle_caret("0.2.3") == [">=0.2.3", "<0.3.0"]

    def test_caret_patch_only(self):
        assert handle_caret("0.0.3") == [">=0.0.3", "<0.0.4"]

    def test_caret_patch_only_edge_case(self):
        """0.0.x bumps only the patch version."""
        assert handle_caret("0.0.1") == [">=0.0.1", "<0.0.2"]

    def test_caret_minor_only(self):
        """^0.x.y bumps only the minor version."""
        assert handle_caret("0.1.0") == [">=0.1.0", "<0.2.0"]

    def test_caret_returns_list(self):
        result = handle_caret("2.0.0")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_caret_upper_bound_increments_major(self):
        result = handle_caret("5.4.3")
        assert result[0] == ">=5.4.3"
        assert result[1].startswith("<6")


class TestHandleTilde:
    """handle_tilde must correctly translate npm-style tilde ranges to PEP 440."""

    def test_tilde_patch_level(self):
        assert handle_tilde("1.2.3") == [">=1.2.3", "<1.3.0"]

    def test_tilde_minor_level(self):
        assert handle_tilde("1.2") == [">=1.2", "<1.3.0"]

    def test_tilde_major_level(self):
        assert handle_tilde("1") == [">=1", "<1.1.0"]

    def test_tilde_returns_list(self):
        result = handle_tilde("2.0.0")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_tilde_upper_bound_increments_minor(self):
        result = handle_tilde("5.4.3")
        assert result[0] == ">=5.4.3"
        assert result[1].startswith("<5.5")


class TestHandleWildcard:
    """handle_wildcard must correctly translate wildcard versions to PEP 440 ranges."""

    def test_wildcard_major_x_replacement(self):
        """1.x should expand to >=1.0.0,<2.0.0."""
        result = handle_wildcard("1.x")
        assert len(result) == 2
        assert result[0] == ">=1.0.0"
        assert result[1] == "<2.0.0"

    def test_wildcard_star_replacement(self):
        """1.* should behave like 1.x."""
        result = handle_wildcard("1.*")
        assert result[0] == ">=1.0.0"
        assert result[1] == "<2.0.0"

    def test_wildcard_minor_level(self):
        """1.2.x should expand to >=1.2.0,<1.3.0."""
        result = handle_wildcard("1.2.x")
        assert result[0] == ">=1.2.0"
        assert result[1] == "<1.3.0"

    def test_wildcard_partial_major_preserves_leading_zero(self):
        """01.x preserves the leading zero as written."""
        result = handle_wildcard("01.x")
        assert ">=01.0.0" in result

    def test_wildcard_single_number_returns_empty(self):
        """A bare major version number has no wildcards to expand."""
        result = handle_wildcard("1")
        assert result == []

    def test_wildcard_three_part_exact_returns_empty(self):
        """A fully-specified version has no wildcards to expand."""
        result = handle_wildcard("1.2.3")
        assert result == []

    def test_wildcard_returns_list(self):
        result = handle_wildcard("2.x")
        assert isinstance(result, list)

    def test_wildcard_x_replacement_behaves_like_star(self):
        """x and * should be interchangeable."""
        assert handle_wildcard("2.x") == handle_wildcard("2.*")
        assert handle_wildcard("2.3.x") == handle_wildcard("2.3.*")
