"""
Unit tests for backend/secuscan/capabilities _SAFETY_LEVEL_IMPLIED mapping.

_SAFETY_LEVEL_IMPLIED maps plugin safety levels ("safe", "intrusive", "exploit")
to their implied capability sets. This mapping is critical for backward compatibility
of plugins that do not declare explicit capabilities. This test file directly tests
the mapping structure and its integration with effective_capabilities.

Run with:
    python3 -m pytest testing/backend/unit/test_capabilities_safety_implied.py -v --noconftest
"""

from __future__ import annotations

import pytest

from backend.secuscan.capabilities import (
    ALL_CAPABILITIES,
    _SAFETY_LEVEL_IMPLIED,
    effective_capabilities,
)


class TestSafetyLevelImpliedMapping:
    """Tests for the structure of _SAFETY_LEVEL_IMPLIED."""

    def test_has_exactly_three_entries(self):
        """_SAFETY_LEVEL_IMPLIED must have exactly 3 entries."""
        assert len(_SAFETY_LEVEL_IMPLIED) == 3

    def test_has_safe_key(self):
        """_SAFETY_LEVEL_IMPLIED must have a 'safe' key."""
        assert "safe" in _SAFETY_LEVEL_IMPLIED

    def test_has_intrusive_key(self):
        """_SAFETY_LEVEL_IMPLIED must have an 'intrusive' key."""
        assert "intrusive" in _SAFETY_LEVEL_IMPLIED

    def test_has_exploit_key(self):
        """_SAFETY_LEVEL_IMPLIED must have an 'exploit' key."""
        assert "exploit" in _SAFETY_LEVEL_IMPLIED


class TestSafetyLevelImpliedContents:
    """Tests for the implied capability sets."""

    def test_safe_implies_only_network(self):
        """The 'safe' safety level must imply only 'network' capability."""
        implied = _SAFETY_LEVEL_IMPLIED["safe"]
        assert isinstance(implied, list)
        assert set(implied) == {"network"}

    def test_intrusive_implies_network_and_intrusive(self):
        """The 'intrusive' safety level must imply 'network' and 'intrusive'."""
        implied = _SAFETY_LEVEL_IMPLIED["intrusive"]
        assert isinstance(implied, list)
        assert set(implied) == {"network", "intrusive"}

    def test_exploit_implies_network_intrusive_exploit(self):
        """The 'exploit' safety level must imply 'network', 'intrusive', and 'exploit'."""
        implied = _SAFETY_LEVEL_IMPLIED["exploit"]
        assert isinstance(implied, list)
        assert set(implied) == {"network", "intrusive", "exploit"}

    def test_no_implied_set_is_empty(self):
        """No implied set may be empty."""
        for level, implied in _SAFETY_LEVEL_IMPLIED.items():
            assert len(implied) > 0, f"Safety level '{level}' has an empty implied set"


class TestSafetyLevelImpliedCapabilities:
    """Tests that all implied capabilities are valid (members of ALL_CAPABILITIES)."""

    @pytest.mark.parametrize("level", list(_SAFETY_LEVEL_IMPLIED.keys()))
    def test_all_implied_capabilities_are_valid(self, level):
        """Every implied capability must be a member of ALL_CAPABILITIES."""
        for cap in _SAFETY_LEVEL_IMPLIED[level]:
            assert cap in ALL_CAPABILITIES, (
                f"Implied capability '{cap}' for safety level '{level}' "
                f"is not in ALL_CAPABILITIES"
            )


class TestSafetyLevelImpliedEffectiveCapabilities:
    """Tests for effective_capabilities integration with _SAFETY_LEVEL_IMPLIED."""

    def test_none_declared_safe_returns_network(self):
        """None declared with 'safe' level must return the 'safe' implied set."""
        result = effective_capabilities(None, "safe", "test-plugin")
        assert result == {"network"}

    def test_none_declared_intrusive_returns_network_and_intrusive(self):
        """None declared with 'intrusive' level must return the 'intrusive' implied set."""
        result = effective_capabilities(None, "intrusive", "test-plugin")
        assert result == {"network", "intrusive"}

    def test_none_declared_exploit_returns_all_three(self):
        """None declared with 'exploit' level must return the 'exploit' implied set."""
        result = effective_capabilities(None, "exploit", "test-plugin")
        assert result == {"network", "intrusive", "exploit"}

    def test_empty_declared_uses_implied(self):
        """An empty declared list must use the implied set for the safety level."""
        result = effective_capabilities([], "intrusive", "test-plugin")
        # Empty declared list should fall through to implied
        assert len(result) > 0

    def test_unknown_safety_level_defaults_to_network(self):
        """An unknown safety level must default to the 'safe' implied set."""
        result = effective_capabilities(None, "unknown_level", "test-plugin")
        assert result == {"network"}

    def test_network_in_all_implied_sets(self):
        """'network' must be in the implied set for every safety level."""
        for level, implied in _SAFETY_LEVEL_IMPLIED.items():
            assert "network" in implied, (
                f"Safety level '{level}' does not include 'network'"
            )

