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
"""

import json
from pathlib import Path

import pytest

from backend.secuscan.capabilities import ALL_CAPABILITIES, CapabilityEnforcer


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
