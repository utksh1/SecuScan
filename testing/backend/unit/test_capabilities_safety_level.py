"""
Unit tests for _SAFETY_LEVEL_IMPLIED mapping in backend/secuscan/capabilities.py

Covers:
- All 3 SafetyLevel enum values have an entry in _SAFETY_LEVEL_IMPLIED
- Each entry is a list (not None, not string)
- Implied capability lists are not empty
- Implied capabilities are strings
- Each implied capability is unique within its list
- SAFE implies only "network"
- INTRUSIVE implies both "network" and "intrusive"
- EXPLOIT implies "network", "intrusive", and "exploit"
"""

from __future__ import annotations

import pytest

from backend.secuscan.capabilities import _SAFETY_LEVEL_IMPLIED
from backend.secuscan.models import SafetyLevel


class TestSafetyLevelImpliedCompleteness:
    def test_all_three_safety_levels_have_entry(self):
        """All three SafetyLevel enum values are present as keys."""
        for level in SafetyLevel:
            assert level.value in _SAFETY_LEVEL_IMPLIED, f"Missing entry for {level.value}"

    def test_all_entries_are_lists(self):
        """Every value in _SAFETY_LEVEL_IMPLIED is a list."""
        for key, value in _SAFETY_LEVEL_IMPLIED.items():
            assert isinstance(value, list), f"Entry for '{key}' is not a list: {type(value)}"

    def test_all_entries_are_non_empty(self):
        """Every implied capability list is non-empty."""
        for key, value in _SAFETY_LEVEL_IMPLIED.items():
            assert len(value) > 0, f"Entry for '{key}' is an empty list"

    def test_all_implied_capabilities_are_strings(self):
        """Every item in every implied capability list is a string."""
        for level, caps in _SAFETY_LEVEL_IMPLIED.items():
            for cap in caps:
                assert isinstance(cap, str), f"Non-string capability '{cap}' in level '{level}'"


class TestSafetyLevelImpliedValues:
    def test_safe_implies_only_network(self):
        """The SAFE safety level implies only the 'network' capability."""
        caps = _SAFETY_LEVEL_IMPLIED["safe"]
        assert caps == ["network"]

    def test_intrusive_implies_network_and_intrusive(self):
        """The INTRUSIVE safety level implies 'network' and 'intrusive'."""
        caps = _SAFETY_LEVEL_IMPLIED["intrusive"]
        assert set(caps) == {"network", "intrusive"}

    def test_exploit_implies_all_three_capabilities(self):
        """The EXPLOIT safety level implies all three capabilities."""
        caps = _SAFETY_LEVEL_IMPLIED["exploit"]
        assert set(caps) == {"network", "intrusive", "exploit"}

    def test_implied_capabilities_are_unique_per_level(self):
        """No safety level has duplicate implied capabilities."""
        for level, caps in _SAFETY_LEVEL_IMPLIED.items():
            assert len(caps) == len(set(caps)), f"Duplicate capabilities in '{level}'"


class TestSafetyLevelProgression:
    def test_higher_safety_level_implies_more_capabilities(self):
        """Each higher safety level implies strictly more capabilities."""
        assert len(_SAFETY_LEVEL_IMPLIED["safe"]) < len(_SAFETY_LEVEL_IMPLIED["intrusive"])
        assert len(_SAFETY_LEVEL_IMPLIED["intrusive"]) < len(_SAFETY_LEVEL_IMPLIED["exploit"])

    def test_network_capability_implied_by_all_levels(self):
        """The 'network' capability is implied by all safety levels."""
        for level in _SAFETY_LEVEL_IMPLIED:
            assert "network" in _SAFETY_LEVEL_IMPLIED[level], f"'network' missing from '{level}'"

    def test_intrusive_capability_implied_by_intrusive_and_exploit(self):
        """The 'intrusive' capability is implied by INTRUSIVE and EXPLOIT but not SAFE."""
        assert "intrusive" in _SAFETY_LEVEL_IMPLIED["intrusive"]
        assert "intrusive" in _SAFETY_LEVEL_IMPLIED["exploit"]
        assert "intrusive" not in _SAFETY_LEVEL_IMPLIED["safe"]

    def test_exploit_capability_only_implied_by_exploit(self):
        """The 'exploit' capability is only implied by EXPLOIT level."""
        assert "exploit" in _SAFETY_LEVEL_IMPLIED["exploit"]
        assert "exploit" not in _SAFETY_LEVEL_IMPLIED["safe"]
        assert "exploit" not in _SAFETY_LEVEL_IMPLIED["intrusive"]
