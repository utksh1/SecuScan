"""
Unit tests for effective_capabilities in backend/secuscan/capabilities.py.

Verifies the plugin capability resolution logic: explicit declarations take
precedence, and legacy plugins without declarations get implied capabilities
based on their safety level.
"""

from backend.secuscan.capabilities import effective_capabilities


class TestEffectiveCapabilities:
    def test_declared_list_returns_declared(self):
        """Declared capability list is returned as-is when non-empty."""
        result = effective_capabilities(["network", "filesystem"], "safe", "plugin-x")
        assert result == {"network", "filesystem"}

    def test_declared_order_ignored(self):
        """Declared capabilities are returned as a set (order-independent)."""
        result = effective_capabilities(["filesystem", "network"], "safe", "plugin-y")
        assert result == {"network", "filesystem"}

    def test_declared_empty_treated_as_none(self):
        """Empty declared list is treated the same as None (uses implied)."""
        result = effective_capabilities([], "intrusive", "plugin-z")
        # Empty list should fall through to implied, not return empty set
        assert len(result) > 0

    def test_implied_safe_returns_network(self):
        """Safety level 'safe' implies only 'network' capability."""
        result = effective_capabilities(None, "safe", "legacy-plugin")
        assert result == {"network"}

    def test_implied_intrusive_returns_network_and_intrusive(self):
        """Safety level 'intrusive' implies 'network' and 'intrusive'."""
        result = effective_capabilities(None, "intrusive", "legacy-plugin")
        assert result == {"network", "intrusive"}

    def test_implied_exploit_returns_all_three(self):
        """Safety level 'exploit' implies 'network', 'intrusive', and 'exploit'."""
        result = effective_capabilities(None, "exploit", "legacy-plugin")
        assert result == {"network", "intrusive", "exploit"}

    def test_implied_unknown_safety_level_defaults_to_network(self):
        """Unknown safety level defaults to 'network' (backward-compatible)."""
        result = effective_capabilities(None, "unknown_level", "legacy-plugin")
        assert result == {"network"}

    def test_none_declared_uses_implied_for_safe(self):
        """None declared with 'safe' level returns the implied set."""
        result = effective_capabilities(None, "safe", "test-plugin")
        assert isinstance(result, set)
        assert "network" in result

    def test_declared_single_capability(self):
        """Single declared capability is preserved."""
        result = effective_capabilities(["docker"], "safe", "docker-plugin")
        assert result == {"docker"}

    def test_declared_deduplicates(self):
        """Duplicate entries in declared list are deduplicated."""
        result = effective_capabilities(["network", "network", "network"], "safe", "plugin")
        assert result == {"network"}
