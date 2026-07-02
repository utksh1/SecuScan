"""
Unit tests for the per-plugin capability enforcement system.

Covers:
- CapabilityEnforcer allows plugins whose capabilities are not denied
- CapabilityEnforcer blocks plugins that require a denied capability
- Partial denial: only the matching capability triggers a block
- Empty denied set: all plugins pass
- Legacy plugins (no declared capabilities) fall back to safety-level implied set
- validate_capability_list rejects unknown tokens
- effective_capabilities logic for declared vs implied sets
- Exploit capability is correctly blocked/allowed
- CapabilityDeniedError carries the right metadata
- build_enforcer_from_settings round-trips through Settings
"""

import pytest
from unittest.mock import patch

from backend.secuscan.capabilities import (
    ALL_CAPABILITIES,
    Capability,
    CapabilityDeniedError,
    CapabilityEnforcer,
    effective_capabilities,
    validate_capability_list,
    build_enforcer_from_settings,
)


# ---------------------------------------------------------------------------
# validate_capability_list
# ---------------------------------------------------------------------------


class TestValidateCapabilityList:
    def test_all_known_capabilities_accepted(self):
        known = list(ALL_CAPABILITIES)
        result = validate_capability_list(known, "test_plugin")
        assert set(result) == ALL_CAPABILITIES

    def test_unknown_token_raises(self):
        with pytest.raises(ValueError, match="unknown capability"):
            validate_capability_list(["network", "xray_vision"], "test_plugin")

    def test_empty_list_is_valid(self):
        assert validate_capability_list([], "test_plugin") == []

    def test_normalises_to_lowercase(self):
        result = validate_capability_list(["NETWORK", "Intrusive"], "test_plugin")
        assert result == ["network", "intrusive"]

    def test_whitespace_is_stripped(self):
        result = validate_capability_list(["  network  "], "test_plugin")
        assert result == ["network"]


# ---------------------------------------------------------------------------
# effective_capabilities
# ---------------------------------------------------------------------------


class TestEffectiveCapabilities:
    def test_explicit_list_returned_as_is(self):
        caps = effective_capabilities(["network", "credentials"], "safe", "plugin")
        assert caps == {"network", "credentials"}

    def test_empty_declared_list_falls_back_to_implied(self):
        # An *empty* list (no capabilities declared) falls back to implied
        caps = effective_capabilities(None, "safe", "plugin")
        assert "network" in caps

    def test_intrusive_implied_set(self):
        caps = effective_capabilities(None, "intrusive", "plugin")
        assert caps >= {"network", "intrusive"}

    def test_exploit_implied_set(self):
        caps = effective_capabilities(None, "exploit", "plugin")
        assert caps >= {"network", "intrusive", "exploit"}

    def test_safe_implied_set(self):
        caps = effective_capabilities(None, "safe", "plugin")
        assert "network" in caps
        assert "exploit" not in caps

    def test_explicit_empty_list_falls_back_to_implied(self):
        # An empty list [] means "no explicit declarations" → use implied
        caps = effective_capabilities([], "intrusive", "plugin")
        assert "intrusive" in caps

    def test_explicit_list_overrides_implied(self):
        # Plugin explicitly declares only "filesystem" even though it's intrusive
        caps = effective_capabilities(["filesystem"], "intrusive", "plugin")
        assert caps == {"filesystem"}
        assert "network" not in caps


# ---------------------------------------------------------------------------
# CapabilityEnforcer – basic allow/deny
# ---------------------------------------------------------------------------


class TestCapabilityEnforcerAllow:
    def test_no_denied_capabilities_always_passes(self):
        enforcer = CapabilityEnforcer(denied_capabilities=[])
        # Should not raise for any combination
        enforcer.check("nuclei", ["network", "intrusive"], "intrusive")
        enforcer.check("sqlmap", ["network", "intrusive", "exploit"], "exploit")
        enforcer.check("nmap", ["network"], "safe")

    def test_unrelated_denial_does_not_block(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["docker"])
        enforcer.check("nmap", ["network"], "safe")

    def test_plugin_passes_when_all_its_caps_allowed(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["exploit"])
        enforcer.check("nuclei", ["network", "intrusive"], "intrusive")

    def test_exploit_plugin_allowed_when_exploit_not_denied(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["docker"])
        enforcer.check("sqlmap", ["network", "intrusive", "exploit"], "exploit")


class TestCapabilityEnforcerDeny:
    def test_single_denied_capability_blocks(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["exploit"])
        with pytest.raises(CapabilityDeniedError) as exc_info:
            enforcer.check("sqlmap", ["network", "intrusive", "exploit"], "exploit")
        assert "exploit" in str(exc_info.value)

    def test_blocks_when_any_required_cap_denied(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["intrusive"])
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("nuclei", ["network", "intrusive"], "intrusive")

    def test_multiple_denied_some_matching(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["docker", "exploit"])
        with pytest.raises(CapabilityDeniedError) as exc_info:
            enforcer.check("zap", ["network", "exploit"], "exploit")
        error = exc_info.value
        assert "exploit" in error.denied_capabilities

    def test_error_carries_plugin_id(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["credentials"])
        with pytest.raises(CapabilityDeniedError) as exc_info:
            enforcer.check("ssh_runner", ["network", "credentials"], "intrusive")
        assert exc_info.value.plugin_id == "ssh_runner"

    def test_error_carries_denied_set(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["exploit", "credentials"])
        with pytest.raises(CapabilityDeniedError) as exc_info:
            enforcer.check("metasploit", ["network", "exploit", "credentials"], "exploit")
        blocked = exc_info.value.denied_capabilities
        assert "exploit" in blocked
        assert "credentials" in blocked

    def test_legacy_plugin_no_caps_blocked_via_implied(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["exploit"])
        with pytest.raises(CapabilityDeniedError):
            # No declared capabilities, safety=exploit → implied includes exploit
            enforcer.check("legacy_exploiter", None, "exploit")

    def test_legacy_intrusive_plugin_blocked(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["intrusive"])
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("old_scanner", None, "intrusive")

    def test_legacy_safe_plugin_not_blocked_by_intrusive_denial(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["intrusive"])
        # Safe plugin implied set does not include intrusive
        enforcer.check("passive_scanner", None, "safe")

    def test_filesystem_denial_blocks_filesystem_plugin(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["filesystem"])
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("yara_scan", ["filesystem", "intrusive"], "intrusive")

    def test_docker_denial_blocks_docker_plugin(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["docker"])
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("container_scanner", ["network", "docker"], "safe")


# ---------------------------------------------------------------------------
# CapabilityEnforcer – denied set normalisation
# ---------------------------------------------------------------------------


class TestCapabilityEnforcerNormalisation:
    def test_whitespace_in_denied_list_stripped(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["  exploit  "])
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("sqlmap", ["exploit"], "exploit")

    def test_uppercase_denied_capability_normalised(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["EXPLOIT"])
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("sqlmap", ["exploit"], "exploit")

    def test_empty_strings_in_denied_list_ignored(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["", " ", "network"])
        enforcer.check("nmap", ["filesystem"], "safe")

    def test_denied_property_is_frozenset(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["network", "exploit"])
        assert isinstance(enforcer.denied, frozenset)


# ---------------------------------------------------------------------------
# CapabilityDeniedError
# ---------------------------------------------------------------------------


class TestCapabilityDeniedError:
    def test_message_contains_plugin_id(self):
        err = CapabilityDeniedError("my_plugin", {"exploit"})
        assert "my_plugin" in str(err)

    def test_message_contains_capability_name(self):
        err = CapabilityDeniedError("my_plugin", {"credentials", "exploit"})
        assert "credentials" in str(err)
        assert "exploit" in str(err)

    def test_is_permission_error(self):
        err = CapabilityDeniedError("my_plugin", {"exploit"})
        assert isinstance(err, PermissionError)


# ---------------------------------------------------------------------------
# build_enforcer_from_settings
# ---------------------------------------------------------------------------


class TestBuildEnforcerFromSettings:
    def test_empty_denied_capabilities_in_settings(self):
        with patch("backend.secuscan.config.settings") as mock_settings:
            mock_settings.denied_capabilities = []
            enforcer = build_enforcer_from_settings()
            assert enforcer.denied == frozenset()

    def test_denied_capabilities_propagated_from_settings(self):
        with patch("backend.secuscan.config.settings") as mock_settings:
            mock_settings.denied_capabilities = ["exploit", "docker"]
            enforcer = build_enforcer_from_settings()
            assert "exploit" in enforcer.denied
            assert "docker" in enforcer.denied

    def test_enforcer_blocks_based_on_settings(self):
        with patch("backend.secuscan.config.settings") as mock_settings:
            mock_settings.denied_capabilities = ["exploit"]
            enforcer = build_enforcer_from_settings()
            with pytest.raises(CapabilityDeniedError):
                enforcer.check("sqlmap", ["network", "exploit"], "exploit")

    def test_build_enforcer_from_settings_ignores_extra_keys(self):
        """Extra/unexpected keys in the settings object should be ignored."""
        with patch("backend.secuscan.config.settings") as mock_settings:
            mock_settings.denied_capabilities = ["docker"]
            mock_settings.extra_unknown_key = "should_be_ignored"
            mock_settings.another_extra = ["not", "used"]
            enforcer = build_enforcer_from_settings()
            # Only denied_capabilities should affect the enforcer
            assert enforcer.denied == frozenset({"docker"})
            assert "exploit" not in enforcer.denied
