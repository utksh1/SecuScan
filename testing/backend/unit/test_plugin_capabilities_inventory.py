"""
Plugin capability inventory tests (PR #368).

Verifies:
- Every plugin whose metadata.json declares a `capabilities` field uses only
  recognised capability tokens from the ALL_CAPABILITIES set.
- Plugins with safety.level == "exploit" that declare explicit capabilities
  include the "exploit" token (high-risk classification consistency).
- CapabilityEnforcer raises ValueError at construction time on an unknown
  denied-capability token (operator typo safety).
- CapabilityEnforcer raises on any unknown token even when mixed with valid ones.
- CapabilityEnforcer accepts the empty denied list without error.
- CapabilityEnforcer accepts all recognised capability tokens without error.
- Denied capabilities raise CapabilityDeniedError BEFORE command construction
  (execution-blocking regression: executor must enforce policy before any
  subprocess is spawned or any command argument is assembled).
- effective_capabilities returns the expected implied set for every known
  safety level so legacy plugins remain enforceable without metadata changes.
"""

import json
from pathlib import Path
import pytest

from backend.secuscan.capabilities import (
    ALL_CAPABILITIES,
    CapabilityDeniedError,
    CapabilityEnforcer,
    effective_capabilities,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLUGINS_ROOT = Path(__file__).parent.parent.parent.parent / "plugins"


def _iter_plugin_metadata():
    """Yield (plugin_id, metadata_dict) for every plugin with a metadata.json."""
    for plugin_dir in sorted(_PLUGINS_ROOT.iterdir()):
        mf = plugin_dir / "metadata.json"
        if not mf.is_file():
            continue
        try:
            meta = json.loads(mf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        yield meta.get("id", plugin_dir.name), meta


def _plugins_with_explicit_capabilities():
    return [
        (pid, meta)
        for pid, meta in _iter_plugin_metadata()
        if meta.get("capabilities") is not None
    ]


def _exploit_plugins_with_explicit_capabilities():
    return [
        (pid, meta)
        for pid, meta in _plugins_with_explicit_capabilities()
        if meta.get("safety", {}).get("level") == "exploit"
    ]


# ---------------------------------------------------------------------------
# Capability token inventory
# ---------------------------------------------------------------------------


class TestPluginCapabilityInventory:
    def test_all_declared_capabilities_are_recognised(self):
        """Every capability token declared in any plugin metadata.json must be
        in ALL_CAPABILITIES; unknown tokens indicate a typo or an undocumented
        capability that was never registered."""
        bad: list[str] = []
        for plugin_id, meta in _plugins_with_explicit_capabilities():
            for token in meta.get("capabilities", []):
                if token.strip().lower() not in ALL_CAPABILITIES:
                    bad.append(f"{plugin_id}: unknown token {token!r}")
        assert not bad, (
            "Plugin(s) declare unrecognised capability tokens:\n"
            + "\n".join(bad)
            + f"\nSupported: {sorted(ALL_CAPABILITIES)}"
        )

    def test_exploit_level_plugins_declare_exploit_capability(self):
        """Plugins with safety.level == 'exploit' that explicitly declare
        capabilities must include 'exploit' — omitting it would let the
        operator's deny-list miss them."""
        missing: list[str] = []
        for plugin_id, meta in _exploit_plugins_with_explicit_capabilities():
            caps = [t.strip().lower() for t in meta.get("capabilities", [])]
            if "exploit" not in caps:
                missing.append(plugin_id)
        assert not missing, (
            "Exploit-level plugin(s) declare explicit capabilities but omit "
            f"'exploit': {missing}. Add 'exploit' or remove the explicit "
            "declaration to fall back to the implied set."
        )

    def test_intrusive_level_plugins_declare_intrusive_when_explicit(self):
        """Plugins with safety.level == 'intrusive' that explicitly declare
        capabilities must include 'intrusive'."""
        missing: list[str] = []
        for plugin_id, meta in _plugins_with_explicit_capabilities():
            if meta.get("safety", {}).get("level") != "intrusive":
                continue
            caps = [t.strip().lower() for t in meta.get("capabilities", [])]
            if "intrusive" not in caps:
                missing.append(plugin_id)
        assert not missing, (
            "Intrusive-level plugin(s) declare explicit capabilities but omit "
            f"'intrusive': {missing}."
        )

    def test_capabilities_field_is_a_list_when_present(self):
        """The `capabilities` field must be a JSON array, not a string or other type."""
        bad: list[str] = []
        for plugin_id, meta in _plugins_with_explicit_capabilities():
            if not isinstance(meta.get("capabilities"), list):
                bad.append(
                    f"{plugin_id}: 'capabilities' is {type(meta['capabilities']).__name__}, "
                    "expected list"
                )
        assert not bad, "\n".join(bad)

    def test_all_capability_tokens_are_lowercase_strings(self):
        """Capability tokens should be lowercase strings (normalisation happens at
        runtime, but storing mixed-case values is a maintenance footgun)."""
        bad: list[str] = []
        for plugin_id, meta in _plugins_with_explicit_capabilities():
            for token in meta.get("capabilities", []):
                if not isinstance(token, str) or token != token.lower():
                    bad.append(f"{plugin_id}: non-lowercase token {token!r}")
        assert not bad, "\n".join(bad)

    def test_all_shipped_plugins_declare_capabilities(self):
        """Every bundled plugin must declare an explicit capabilities list."""
        missing: list[str] = []
        for plugin_id, meta in _iter_plugin_metadata():
            caps = meta.get("capabilities")
            if not isinstance(caps, list) or not caps:
                missing.append(plugin_id)
        assert not missing, (
            "Bundled plugin(s) missing explicit capabilities declarations: "
            f"{missing}"
        )


# ---------------------------------------------------------------------------
# CapabilityEnforcer construction-time token validation
# ---------------------------------------------------------------------------


class TestCapabilityEnforcerDeniedTokenValidation:
    def test_unknown_token_raises_at_construction(self):
        with pytest.raises(ValueError, match="unrecognised capability"):
            CapabilityEnforcer(denied_capabilities=["netwrk"])  # typo

    def test_mixed_valid_and_unknown_raises(self):
        with pytest.raises(ValueError, match="unrecognised capability"):
            CapabilityEnforcer(denied_capabilities=["network", "xray_vision"])

    def test_error_message_names_the_bad_token(self):
        with pytest.raises(ValueError, match="xray_vision"):
            CapabilityEnforcer(denied_capabilities=["xray_vision"])

    def test_error_message_lists_supported_capabilities(self):
        with pytest.raises(ValueError, match="Supported capabilities"):
            CapabilityEnforcer(denied_capabilities=["bad_token"])

    def test_empty_denied_list_accepted(self):
        enforcer = CapabilityEnforcer(denied_capabilities=[])
        assert enforcer.denied == frozenset()

    def test_none_denied_list_accepted(self):
        enforcer = CapabilityEnforcer(denied_capabilities=None)
        assert enforcer.denied == frozenset()

    def test_all_recognised_tokens_accepted(self):
        enforcer = CapabilityEnforcer(denied_capabilities=list(ALL_CAPABILITIES))
        assert enforcer.denied == ALL_CAPABILITIES

    def test_whitespace_only_tokens_are_ignored(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["  ", "\t", "network"])
        assert "network" in enforcer.denied

    def test_case_insensitive_normalisation(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["NETWORK", "Exploit"])
        assert "network" in enforcer.denied
        assert "exploit" in enforcer.denied


# ---------------------------------------------------------------------------
# effective_capabilities — implied set correctness for all safety levels
# ---------------------------------------------------------------------------


class TestEffectiveCapabilitiesImpliedSets:
    """Verify the implied capability sets for all safety levels so that
    legacy plugins (those without an explicit 'capabilities' field) remain
    enforceable via deny-list even after the enforcement engine ships."""

    def test_safe_implies_network(self):
        caps = effective_capabilities(None, "safe", "plugin")
        assert "network" in caps

    def test_safe_does_not_imply_intrusive_or_exploit(self):
        caps = effective_capabilities(None, "safe", "plugin")
        assert "intrusive" not in caps
        assert "exploit" not in caps

    def test_intrusive_implies_network_and_intrusive(self):
        caps = effective_capabilities(None, "intrusive", "plugin")
        assert {"network", "intrusive"} <= caps

    def test_intrusive_does_not_imply_exploit(self):
        caps = effective_capabilities(None, "intrusive", "plugin")
        assert "exploit" not in caps

    def test_exploit_implies_network_intrusive_and_exploit(self):
        caps = effective_capabilities(None, "exploit", "plugin")
        assert {"network", "intrusive", "exploit"} <= caps

    def test_unknown_level_falls_back_to_network(self):
        caps = effective_capabilities(None, "unknown_level", "plugin")
        assert "network" in caps

    def test_explicit_empty_list_falls_back_to_implied(self):
        caps = effective_capabilities([], "intrusive", "plugin")
        assert "intrusive" in caps

    def test_explicit_nonempty_list_overrides_implied(self):
        # Plugin explicitly declares only filesystem; implied intrusive set is NOT added.
        caps = effective_capabilities(["filesystem"], "intrusive", "plugin")
        assert caps == {"filesystem"}
        assert "intrusive" not in caps

    def test_all_shipped_plugins_have_enforceable_effective_capabilities(self):
        """Every plugin in the plugins/ directory must produce a non-empty
        effective_capabilities set so the enforcer can act on it."""
        bad: list[str] = []
        for plugin_id, meta in _iter_plugin_metadata():
            level = meta.get("safety", {}).get("level", "safe")
            declared = meta.get("capabilities")
            caps = effective_capabilities(declared, level, plugin_id)
            if not caps:
                bad.append(plugin_id)
        assert not bad, (
            f"Plugin(s) produced empty effective_capabilities: {bad}"
        )


# ---------------------------------------------------------------------------
# Execution-blocking regression: denied capabilities stop execution BEFORE
# command construction — no subprocess is spawned or command built for a
# plugin whose required capabilities are all denied.
# ---------------------------------------------------------------------------


class TestDeniedCapabilityBlocksExecution:
    """CapabilityEnforcer.check() must raise CapabilityDeniedError before any
    command is built or subprocess is spawned.  These tests exercise the
    enforcer in isolation and then simulate the executor integration point."""

    def test_check_raises_capability_denied_error_for_denied_cap(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["network"])
        with pytest.raises(CapabilityDeniedError) as exc_info:
            enforcer.check("my_plugin", declared=None, safety_level="safe")
        assert exc_info.value.plugin_id == "my_plugin"
        assert "network" in exc_info.value.denied_capabilities

    def test_check_raises_before_command_construction(self):
        """Simulate the executor integration point: enforcer.check() is called
        before plugin_manager.build_command().  When the capability is denied,
        build_command must never be called."""
        enforcer = CapabilityEnforcer(denied_capabilities=["exploit"])
        build_command_called: list[bool] = []

        def fake_build_command(*args, **kwargs):
            build_command_called.append(True)
            return ["exploit_tool", "--target", "example.com"]

        with pytest.raises(CapabilityDeniedError):
            enforcer.check("exploit_plugin", declared=None, safety_level="exploit")
            # This line must not be reached:
            fake_build_command("exploit_plugin", {})

        assert build_command_called == [], (
            "build_command must not be called when capability check raises"
        )

    def test_exploit_plugin_blocked_when_exploit_denied(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["exploit"])
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("sqli_exploiter", declared=None, safety_level="exploit")

    def test_intrusive_plugin_blocked_when_intrusive_denied(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["intrusive"])
        with pytest.raises(CapabilityDeniedError):
            enforcer.check("nikto", declared=None, safety_level="intrusive")

    def test_safe_plugin_passes_when_only_exploit_denied(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["exploit"])
        # Should not raise — safe plugins do not require exploit capability.
        enforcer.check("whois_lookup", declared=["network"], safety_level="safe")

    def test_filesystem_only_plugin_passes_when_network_denied(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["network"])
        enforcer.check("code_analyzer", declared=["filesystem"], safety_level="safe")

    def test_plugin_with_explicit_caps_blocked_on_denied_token(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["credentials"])
        with pytest.raises(CapabilityDeniedError) as exc_info:
            enforcer.check(
                "vault_plugin",
                declared=["network", "credentials"],
                safety_level="safe",
            )
        assert "credentials" in exc_info.value.denied_capabilities

    def test_error_message_names_plugin_and_denied_caps(self):
        enforcer = CapabilityEnforcer(denied_capabilities=["docker"])
        with pytest.raises(CapabilityDeniedError) as exc_info:
            enforcer.check("container_scanner", declared=["docker"], safety_level="safe")
        msg = str(exc_info.value)
        assert "container_scanner" in msg
        assert "docker" in msg

    def test_empty_denied_set_never_blocks_any_shipped_plugin(self):
        """With an empty deny list every plugin must pass the capability check."""
        enforcer = CapabilityEnforcer(denied_capabilities=[])
        for plugin_id, meta in _iter_plugin_metadata():
            level = meta.get("safety", {}).get("level", "safe")
            declared = meta.get("capabilities")
            # Must not raise.
            enforcer.check(plugin_id, declared=declared, safety_level=level)

    def test_deny_exploit_blocks_all_exploit_level_shipped_plugins(self):
        """Denying 'exploit' must block every plugin with safety.level == 'exploit'
        regardless of whether they have an explicit capabilities declaration."""
        enforcer = CapabilityEnforcer(denied_capabilities=["exploit"])
        blocked: list[str] = []
        not_blocked: list[str] = []
        for plugin_id, meta in _iter_plugin_metadata():
            if meta.get("safety", {}).get("level") != "exploit":
                continue
            declared = meta.get("capabilities")
            try:
                enforcer.check(plugin_id, declared=declared, safety_level="exploit")
                not_blocked.append(plugin_id)
            except CapabilityDeniedError:
                blocked.append(plugin_id)
        # Every exploit-level plugin must be blocked.
        assert not_blocked == [], (
            f"Exploit-level plugin(s) not blocked when 'exploit' is denied: {not_blocked}"
        )
        # Sanity: at least one exploit-level plugin must exist in the test corpus.
        assert len(blocked) > 0, "No exploit-level plugins found — check plugins/ directory"
