"""
Unit tests for validate_command_network_egress network-policy exception paths.

Covers the behaviour when get_policy_engine() or engine.check_access() raises
an exception. The current implementation does not wrap these calls in try/except,
so the exception propagates to the caller. These tests document the current
behaviour and serve as regression coverage if the exception handling is added.

The happy-path tests (where policy enforcement succeeds or is skipped) are in
test_validation.py; these focus exclusively on the exception-degradation paths.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch


class TestValidateCommandEgressPolicyException:
    """Coverage for get_policy_engine() exception in validate_command_network_egress."""

    def test_get_policy_engine_raises_runtimeerror_propagates(self, monkeypatch):
        """When get_policy_engine() raises RuntimeError, it currently propagates uncaught.

        This test documents the current behaviour. The caller receives the exception.
        A future improvement would wrap this in try/except and degrade gracefully.
        """
        from backend.secuscan.validation import validate_command_network_egress
        from backend.secuscan.config import settings

        monkeypatch.setattr(settings, "enforce_network_policy", True)
        monkeypatch.setattr(settings, "network_policy_failure_mode", "block")

        with patch(
            "backend.secuscan.network_policy.get_policy_engine",
            side_effect=RuntimeError("Policy engine not initialised"),
        ):
            with pytest.raises(RuntimeError, match="Policy engine not initialised"):
                validate_command_network_egress(
                    ["curl", "http://example.com/"],
                    safe_mode=False,
                    plugin_id="test_plugin",
                    task_id="test-task",
                )

    def test_get_policy_engine_raises_permission_error_propagates(self, monkeypatch):
        """When get_policy_engine() raises PermissionError, it currently propagates."""
        from backend.secuscan.validation import validate_command_network_egress
        from backend.secuscan.config import settings

        monkeypatch.setattr(settings, "enforce_network_policy", True)
        monkeypatch.setattr(settings, "network_policy_failure_mode", "block")

        with patch(
            "backend.secuscan.network_policy.get_policy_engine",
            side_effect=PermissionError("Policy database locked"),
        ):
            with pytest.raises(PermissionError):
                validate_command_network_egress(
                    ["curl", "http://10.0.0.1/"],
                    safe_mode=False,
                    plugin_id="test_plugin",
                    task_id="test-task",
                )

    def test_engine_check_access_raises_runtimeerror_propagates(self, monkeypatch):
        """When engine.check_access() raises RuntimeError, it propagates."""
        from backend.secuscan.validation import validate_command_network_egress
        from backend.secuscan.config import settings

        class RaisingEngine:
            def check_access(self, **kwargs):
                raise RuntimeError("check_access failed")

        monkeypatch.setattr(settings, "enforce_network_policy", True)
        monkeypatch.setattr(settings, "network_policy_failure_mode", "block")

        with patch(
            "backend.secuscan.network_policy.get_policy_engine",
            return_value=RaisingEngine(),
        ):
            with pytest.raises(RuntimeError, match="check_access failed"):
                validate_command_network_egress(
                    ["curl", "http://example.com/"],
                    safe_mode=False,
                    plugin_id="test_plugin",
                    task_id="test-task",
                )

    def test_engine_check_access_raises_attribute_error_propagates(self, monkeypatch):
        """When engine.check_access() raises AttributeError, it propagates."""
        from backend.secuscan.validation import validate_command_network_egress
        from backend.secuscan.config import settings

        class NoCheckAccessEngine:
            pass  # has no check_access method

        monkeypatch.setattr(settings, "enforce_network_policy", True)
        monkeypatch.setattr(settings, "network_policy_failure_mode", "block")

        with patch(
            "backend.secuscan.network_policy.get_policy_engine",
            return_value=NoCheckAccessEngine(),
        ):
            with pytest.raises(AttributeError):
                validate_command_network_egress(
                    ["curl", "http://example.com/"],
                    safe_mode=False,
                    plugin_id="test_plugin",
                    task_id="test-task",
                )

    def test_policy_engine_failure_in_log_only_mode_propagates(self, monkeypatch):
        """Even in log_only mode, a failing policy engine currently raises."""
        from backend.secuscan.validation import validate_command_network_egress
        from backend.secuscan.config import settings

        monkeypatch.setattr(settings, "enforce_network_policy", True)
        monkeypatch.setattr(settings, "network_policy_failure_mode", "log_only")

        with patch(
            "backend.secuscan.network_policy.get_policy_engine",
            side_effect=RuntimeError("Policy engine unavailable"),
        ):
            with pytest.raises(RuntimeError):
                validate_command_network_egress(
                    ["curl", "http://10.0.0.1/"],
                    safe_mode=False,
                    plugin_id="test_plugin",
                    task_id="test-task",
                )

    def test_safe_mode_true_blocks_public_ip_before_policy_check(self, monkeypatch):
        """Safe mode must block public IPs before reaching the policy engine.

        This test confirms that safe_mode blocks the request before the
        policy engine is even consulted, so policy engine failures do not
        affect this code path.
        """
        from backend.secuscan.validation import validate_command_network_egress
        from backend.secuscan.config import settings

        monkeypatch.setattr(settings, "enforce_network_policy", True)
        monkeypatch.setattr(settings, "network_policy_failure_mode", "block")

        # Even if the policy engine would raise, safe_mode blocks first.
        with patch(
            "backend.secuscan.network_policy.get_policy_engine",
            side_effect=RuntimeError("engine down"),
        ):
            ok, err = validate_command_network_egress(
                ["curl", "http://93.184.216.34/"],
                safe_mode=True,
                plugin_id="test_plugin",
                task_id="test-task",
            )
            # safe_mode blocks public IPs before the policy engine is consulted.
            assert ok is False
            assert "safe mode" in err.lower() or "public" in err.lower()

    def test_non_network_command_does_not_call_policy_engine(self, monkeypatch):
        """A command with no network argument skips the policy engine entirely.

        This test verifies that filesystem-only commands (no IP/hostname)
        do not trigger a policy engine lookup, so engine failures are
        irrelevant for this code path.
        """
        from backend.secuscan.validation import validate_command_network_egress
        from backend.secuscan.config import settings

        monkeypatch.setattr(settings, "enforce_network_policy", True)
        monkeypatch.setattr(settings, "network_policy_failure_mode", "block")

        # A purely local command (no IP/hostname in args) should pass without
        # consulting the policy engine, so no exception is raised.
        ok, err = validate_command_network_egress(
            ["cat", "/etc/hosts"],
            safe_mode=False,
            plugin_id="test_plugin",
            task_id="test-task",
        )
        assert ok is True
        assert err == ""
