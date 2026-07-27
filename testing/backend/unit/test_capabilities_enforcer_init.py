"""
Unit tests for CapabilityEnforcer initialization edge cases in
backend/secuscan/capabilities.py.

Covers initialization behavior and the denied property that are not
exercised by the existing check() integration tests.
"""

from __future__ import annotations

import pytest

from backend.secuscan.capabilities import (
    ALL_CAPABILITIES,
    CapabilityEnforcer,
    CapabilityDeniedError,
)


# ---------------------------------------------------------------------------
# CapabilityEnforcer initialization
# ---------------------------------------------------------------------------


class TestCapabilityEnforcerDeniedProperty:
    def test_denied_returns_frozenset(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["network", "intrusive"])
        assert isinstance(enforcer.denied, frozenset)

    def test_denied_empty_when_no_denials(self):
        enforcer = CapabilityEnforcer(denied_capabilities=[])
        assert enforcer.denied == frozenset()

    def test_denied_empty_when_none(self):
        enforcer = CapabilityEnforcer(denied_capabilities=None)
        assert enforcer.denied == frozenset()

    def test_denied_contains_normalized_values(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["NETWORK", "INTRUSIVE"])
        assert enforcer.denied == frozenset({"network", "intrusive"})

    def test_denied_does_not_contain_whitespace(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["  filesystem  ", "network"])
        assert "filesystem" in enforcer.denied
        assert "  filesystem  " not in enforcer.denied
        assert "network" in enforcer.denied

    def test_denied_empty_string_in_list_is_skipped(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["network", "", "intrusive"])
        assert enforcer.denied == frozenset({"network", "intrusive"})


class TestCapabilityEnforcerInitValidation:
    def test_unknown_capability_raises_valueerror(self):
        with pytest.raises(ValueError) as exc_info:
            CapabilityEnforcer(denied_capabilities=["network", "not_a_real_capability"])
        assert "not_a_real_capability" in str(exc_info.value)

    def test_unknown_capability_in_list_reports_all_unknown(self):
        with pytest.raises(ValueError) as exc_info:
            CapabilityEnforcer(denied_capabilities=["fake1", "fake2"])
        assert "fake1" in str(exc_info.value)
        assert "fake2" in str(exc_info.value)

    def test_unknown_capability_lists_supported(self):
        with pytest.raises(ValueError) as exc_info:
            CapabilityEnforcer(denied_capabilities=["xyz_unknown"])
        assert "Supported capabilities" in str(exc_info.value)


class TestCapabilityEnforcerCheckDoesNotMutateDenied:
    def test_check_does_not_modify_denied(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["network"])
        original = enforcer.denied
        # sqlmap requires network+intrusive+exploit; blocking network means it raises
        # CapabilityDeniedError, but the denied frozenset is unchanged by the call.
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("sqlmap", ["network", "intrusive", "exploit"], "intrusive")
        assert enforcer.denied == original

    def test_denied_is_frozenset_immutable(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["network"])
        with pytest.raises((TypeError, AttributeError)):
            enforcer.denied.add("intrusive")


class TestCapabilityEnforcerMultipleInstances:
    def test_multiple_enforcers_are_independent(self):
        enforcer1 = CapabilityEnforcer(denied_capabilities=["network"])
        enforcer2 = CapabilityEnforcer(denied_capabilities=["intrusive"])
        assert enforcer1.denied == frozenset({"network"})
        assert enforcer2.denied == frozenset({"intrusive"})


class TestCapabilityEnforcerWithAllCapabilities:
    def test_denied_contains_all_capabilities(self):
        enforcer = CapabilityEnforcer(denied_capabilities=list(ALL_CAPABILITIES))
        assert enforcer.denied == frozenset(ALL_CAPABILITIES)
        assert len(enforcer.denied) == len(ALL_CAPABILITIES)
