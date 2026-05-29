import pytest
import ipaddress
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.secuscan.network_policy import (
    NetworkPolicyEngine, NetworkPolicy, PolicyAction, AuditLogEntry,
    get_policy_engine
)
from backend.secuscan.config import settings

class TestDenyByDefault:
    """Test deny-by-default behavior"""

    def test_empty_allowlist_denies_all(self, tmp_path):
        """Engine with no allowlist should deny all"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))

        allowed, reason, policy = engine.check_access(
            dest_ip="8.8.8.8",
            dest_port=53,
            plugin_id="test",
        )

        assert not allowed
        assert "denied by default" in reason.lower()

    def test_explicit_deny_blocks_immediately(self, tmp_path):
        """Explicit denylist should block before checking allowlist"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_deny_rule("10.0.0.0/8", reason="Internal network")
        engine.add_allow_rule("10.0.0.0/8", reason="Oops, allowed it too")

        allowed, reason, policy = engine.check_access(
            dest_ip="10.1.1.1",
            plugin_id="test",
        )

        assert not allowed
        assert "denylist" in reason.lower()


class TestAllowlistPrecedence:
    """Test allowlist matching"""

    def test_allowlist_permits_access(self, tmp_path):
        """IP in allowlist should be permitted"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_allow_rule("8.8.0.0/16", reason="Google DNS")

        allowed, reason, policy = engine.check_access(
            dest_ip="8.8.8.8",
            plugin_id="test",
        )

        assert allowed
        assert "8.8.0.0/16" in reason

    def test_allowlist_subnet_matching(self, tmp_path):
        """Allowlist should match subnets correctly"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_allow_rule("192.0.2.0/24", reason="Test network")

        # In range
        allowed, _, _ = engine.check_access("192.0.2.100", plugin_id="test")
        assert allowed

        # Out of range
        allowed, _, _ = engine.check_access("192.0.3.100", plugin_id="test")
        assert not allowed


class TestDenylistPrecedence:
    """Test denylist taking priority"""

    def test_denylist_overrides_allowlist(self, tmp_path):
        """Denylist should override allowlist"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_allow_rule("0.0.0.0/0", reason="Allow all")
        engine.add_deny_rule("169.254.169.254/32", reason="AWS metadata")

        allowed, reason, _ = engine.check_access(
            dest_ip="169.254.169.254",
            plugin_id="test",
        )

        assert not allowed
        assert "denylist" in reason.lower()

    def test_denylist_checked_before_allowlist(self, tmp_path):
        """Denylist should be evaluated first for speed"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_allow_rule("10.0.0.0/8", reason="Internal")
        engine.add_deny_rule("10.1.0.0/16", reason="Restricted zone")

        # Should be denied despite being in allowlist
        allowed, reason, _ = engine.check_access(
            dest_ip="10.1.1.1",
            plugin_id="test",
        )

        assert not allowed


class TestIPv6Support:
    """Test IPv6 address handling"""

    def test_ipv6_allowlist(self, tmp_path):
        """IPv6 addresses should be supported"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_allow_rule("2001:4860::/32", reason="Google")

        allowed, _, _ = engine.check_access(
            dest_ip="2001:4860:4860::8888",
            plugin_id="test",
        )

        assert allowed

    def test_ipv6_denylist(self, tmp_path):
        """IPv6 denylist should work"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_deny_rule("fe80::/10", reason="Link-local")

        allowed, _, _ = engine.check_access(
            dest_ip="fe80::1",
            plugin_id="test",
        )

        assert not allowed


class TestAuditLogging:
    """Test audit trail generation"""

    def test_audit_entry_on_allow(self, tmp_path):
        """Allowed connections should be logged"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_allow_rule("8.8.0.0/16", reason="Google DNS")

        engine.check_access(
            dest_ip="8.8.8.8",
            dest_port=53,
            plugin_id="dns_enum",
            task_id="task123",
        )

        assert len(engine.audit_entries) == 1
        entry = engine.audit_entries[0]
        assert entry.action == PolicyAction.ALLOW
        assert entry.dest_ip == "8.8.8.8"
        assert entry.plugin_id == "dns_enum"
        assert entry.task_id == "task123"

    def test_audit_entry_on_deny(self, tmp_path):
        """Denied connections should be logged"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))

        engine.check_access(
            dest_ip="10.0.0.1",
            dest_port=22,
            plugin_id="port_scanner",
            task_id="task456",
        )

        assert len(engine.audit_entries) == 1
        entry = engine.audit_entries[0]
        assert entry.action == PolicyAction.DENY
        assert entry.dest_ip == "10.0.0.1"

    def test_audit_log_file_written(self, tmp_path):
        """Audit entries should be written to file"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_allow_rule("8.8.0.0/16")

        engine.check_access("8.8.8.8", plugin_id="test")

        # Verify file contains JSON entry
        content = audit_log.read_text()
        assert "8.8.8.8" in content
        assert "allow" in content

class TestPolicyExpiration:
    """Test temporary policies"""

    def test_expired_rule_not_evaluated(self, tmp_path):
        """Expired rules should be skipped"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))

        # Add rule that expires in the past
        past = datetime.now() - timedelta(hours=1)
        engine.add_allow_rule("10.0.0.0/8", expires_at=past)

        # Should be denied (rule expired)
        allowed, _, _ = engine.check_access("10.1.1.1", plugin_id="test")
        assert not allowed

    def test_future_rule_is_evaluated(self, tmp_path):
        """Non-expired rules should be evaluated"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))

        future = datetime.now() + timedelta(hours=1)
        engine.add_allow_rule("10.0.0.0/8", expires_at=future)

        allowed, _, _ = engine.check_access("10.1.1.1", plugin_id="test")
        assert allowed

class TestInvalidInput:
    """Test error handling"""

    def test_invalid_cidr_raises_error(self, tmp_path):
        """Invalid CIDR should raise ValueError"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))

        with pytest.raises(ValueError):
            engine.add_allow_rule("not-a-valid-cidr", reason="test")

    def test_invalid_ip_denied(self, tmp_path):
        """Invalid IP format should be denied"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))

        allowed, reason, _ = engine.check_access(
            dest_ip="not-an-ip",
            plugin_id="test",
        )

        assert not allowed
        assert "invalid" in reason.lower()

class TestAuditLogFiltering:
    """Test audit log queries"""

    def test_filter_by_plugin_id(self, tmp_path):
        """Should filter audit entries by plugin"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))

        engine.check_access("8.8.8.8", plugin_id="dns_enum", task_id="1")
        engine.check_access("8.8.8.8", plugin_id="port_scanner", task_id="2")

        entries = engine.get_audit_entries(plugin_id="dns_enum")
        assert len(entries) == 1
        assert entries[0].plugin_id == "dns_enum"

    def test_filter_by_action(self, tmp_path):
        """Should filter audit entries by action"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_allow_rule("8.8.0.0/16")

        engine.check_access("8.8.8.8", plugin_id="test")  # ALLOW
        engine.check_access("10.0.0.1", plugin_id="test")  # DENY

        allow_entries = engine.get_audit_entries(action=PolicyAction.ALLOW)
        assert len(allow_entries) == 1
        assert allow_entries[0].action == PolicyAction.ALLOW
