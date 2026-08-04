"""
Unit tests for get_policy_engine singleton in backend/secuscan/network_policy.py.
"""
import pytest

from backend.secuscan.network_policy import get_policy_engine


def _reset_singleton():
    """Reset the module-level singleton so tests get a fresh engine."""
    import backend.secuscan.network_policy as mod
    mod._policy_engine = None


class TestGetPolicyEngine:
    """Tests for the get_policy_engine singleton accessor."""

    def test_first_call_creates_new_engine_instance(self):
        """First call should return a new NetworkPolicyEngine instance."""
        _reset_singleton()
        engine = get_policy_engine()
        assert engine is not None
        assert hasattr(engine, "check_access")
        assert hasattr(engine, "add_deny_rule")
        assert hasattr(engine, "add_allow_rule")

    def test_second_call_returns_same_instance(self):
        """Subsequent calls must return the exact same instance (singleton)."""
        _reset_singleton()
        engine1 = get_policy_engine()
        engine2 = get_policy_engine()
        assert engine1 is engine2

    def test_engine_has_expected_public_methods(self):
        """Engine must expose the documented public API."""
        _reset_singleton()
        engine = get_policy_engine()
        assert callable(engine.check_access)
        assert callable(engine.add_deny_rule)
        assert callable(engine.add_allow_rule)
        assert callable(engine.export_audit_log)
        assert callable(engine.clear_audit_entries)
        assert callable(engine.get_audit_entries)

    def test_singleton_persists_after_clear_audit_entries(self):
        """Clearing audit entries must not replace the engine instance."""
        _reset_singleton()
        engine1 = get_policy_engine()
        engine1.clear_audit_entries()
        engine2 = get_policy_engine()
        assert engine1 is engine2

    def test_singleton_behavior_across_multiple_calls(self):
        """Multiple get_policy_engine calls always return the same object."""
        _reset_singleton()
        engines = [get_policy_engine() for _ in range(5)]
        assert all(e is engines[0] for e in engines)

    def test_engine_is_initialized_with_correct_settings(self):
        """Engine must be created and have the expected attributes."""
        _reset_singleton()
        engine = get_policy_engine()
        assert engine is not None
        assert hasattr(engine, "_max_audit_entries")
        assert engine._max_audit_entries > 0
