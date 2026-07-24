"""
Unit tests for capability policy enforcement edge cases in
backend/secuscan/capabilities.py.

Covers the CapabilityEnforcer and effective_capabilities edge cases
that are not tested in the existing test_capabilities.py.
"""

import pytest
from unittest.mock import patch

from backend.secuscan.capabilities import (
    CapabilityEnforcer,
    effective_capabilities,
    validate_capability_list,
    CapabilityDeniedError,
    Capability,
)


class TestCapabilityEnforcerEdgeCases:
    """Edge cases for CapabilityEnforcer that the existing tests do not cover."""

    def test_denied_is_frozenset(self):
        """The denied property must always be a frozenset, not a regular set."""
        enforcer = CapabilityEnforcer(denied_capabilities=["exploit", "docker"])
        assert isinstance(enforcer.denied, frozenset)

    def test_denied_is_empty_frozenset_when_no_denials(self):
        """When no capabilities are denied, denied must be an empty frozenset."""
        enforcer = CapabilityEnforcer(denied_capabilities=[])
        assert enforcer.denied == frozenset()

    def test_single_capability_in_denied_list(self):
        """A single capability in the deny list blocks exactly that capability."""
        enforcer = CapabilityEnforcer(denied_capabilities=["docker"])
        assert "docker" in enforcer.denied
        assert "network" not in enforcer.denied

    def test_denied_unknown_capability_raises_with_clear_message(self):
        """An unknown capability name in the deny list raises ValueError with details."""
        with pytest.raises(ValueError) as exc_info:
            CapabilityEnforcer(denied_capabilities=["not_a_real_cap"])
        assert "not_a_real_cap" in str(exc_info.value)

    def test_whitespace_in_denied_list_is_ignored(self):
        """Leading/trailing whitespace in deny list tokens is stripped."""
        enforcer = CapabilityEnforcer(denied_capabilities=["  exploit  ", " docker "])
        assert "exploit" in enforcer.denied
        assert "docker" in enforcer.denied

    def test_case_insensitive_denied_capability(self):
        """Denying EXPLOIT blocks 'exploit' (case-insensitive)."""
        enforcer = CapabilityEnforcer(denied_capabilities=["EXPLOIT"])
        assert "exploit" in enforcer.denied

    def test_check_passes_when_no_capabilities_denied(self):
        """When denied is empty, check() never raises."""
        enforcer = CapabilityEnforcer(denied_capabilities=[])
        # Should not raise for any plugin
        enforcer.check("any_plugin", declared=["exploit"], safety_level="safe")


class TestEffectiveCapabilitiesEdgeCases:
    """Edge cases for effective_capabilities beyond the existing test coverage."""

    def test_unknown_safety_level_defaults_to_network(self):
        """An unknown safety level falls back to the 'safe' implied set."""
        caps = effective_capabilities(None, "unknown_level", "plugin")
        assert caps == {"network"}

    def test_case_insensitive_safety_level(self):
        """Safety level matching is case-insensitive."""
        caps_lower = effective_capabilities(None, "intrusive", "plugin")
        caps_upper = effective_capabilities(None, "INTRUSIVE", "plugin")
        assert caps_lower == caps_upper

    def test_declared_list_deduplicates(self):
        """When the declared list has duplicates, the result is deduplicated."""
        caps = effective_capabilities(["network", "network", "filesystem"], "safe", "plugin")
        assert caps == {"network", "filesystem"}

    def test_all_declared_capabilities_returned(self):
        """All declared capabilities are in the result, in any order."""
        caps = effective_capabilities(
            ["network", "filesystem", "docker", "credentials"], "safe", "plugin"
        )
        assert caps == {"network", "filesystem", "docker", "credentials"}


class TestCapabilityDeniedErrorEdgeCases:
    """Edge cases for CapabilityDeniedError."""

    def test_error_carries_plugin_id(self):
        """The plugin_id attribute is accessible on the error."""
        err = CapabilityDeniedError("my-scanner", {"docker"})
        assert err.plugin_id == "my-scanner"

    def test_error_carries_denied_set(self):
        """The denied_capabilities attribute is accessible on the error."""
        err = CapabilityDeniedError("my-scanner", {"docker", "exploit"})
        assert err.denied_capabilities == {"docker", "exploit"}

    def test_isinstance_permission_error(self):
        """CapabilityDeniedError is a subclass of PermissionError."""
        err = CapabilityDeniedError("plugin", {"exploit"})
        assert isinstance(err, PermissionError)

    def test_error_message_format(self):
        """The error message contains both the plugin id and capability names."""
        err = CapabilityDeniedError("test-plugin", {"credentials"})
        msg = str(err)
        assert "test-plugin" in msg
        assert "credentials" in msg
