import pytest
import ipaddress
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.secuscan.network_policy import (
    NetworkPolicyEngine, NetworkPolicy, PolicyAction, AuditLogEntry,
    get_policy_engine, _init_default_policies
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


class TestInitDefaultPolicies:
    """Test _init_default_policies logic"""

    def test_empty_allowlist_adds_default_public_egress(self, tmp_path):
        """Empty allowlist should add implicit 0.0.0.0/0 and ::/0 rules for public egress"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        _init_default_policies(engine)
        # The engine should have implicit allow-all rules for public egress
        assert len(engine.allowlist) >= 2

    def test_empty_allowlist_blocks_private_ranges(self, tmp_path):
        """Even with implicit public egress, denylisted private ranges must be blocked"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        _init_default_policies(engine)
        # Private/metadata IPs should still be blocked by denylist
        for blocked_ip in ["10.0.0.1", "192.168.1.1", "172.16.0.1",
                           "169.254.169.254", "127.0.0.1", "100.64.0.1"]:
            allowed, _, _ = engine.check_access(blocked_ip, plugin_id="test")
            assert not allowed, f"{blocked_ip} should be blocked by denylist"

    def test_empty_allowlist_allows_public_ips(self, tmp_path):
        """With implicit public egress, public IPs should be allowed"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        _init_default_policies(engine)
        # Public IPs should be allowed
        for public_ip in ["8.8.8.8", "1.1.1.1", "93.184.216.34"]:
            allowed, _, _ = engine.check_access(public_ip, plugin_id="test")
            assert allowed, f"{public_ip} should be allowed by default public egress"

    def test_explicit_allowlist_entries_are_loaded(self, monkeypatch, tmp_path):
        """Entries in SECUSCAN_NETWORK_ALLOWLIST should appear in engine.allowlist"""
        monkeypatch.setattr(
            "backend.secuscan.config.settings.network_allowlist",
            ["8.8.8.8/32", "1.1.1.1/32"],
        )
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        _init_default_policies(engine)
        assert len(engine.allowlist) == 2


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

class TestURLTargetHandling:
    """Test URL and target parsing/cleaning in the policy engine"""

    @patch("socket.gethostbyname")
    def test_url_target_cleaning_and_resolution(self, mock_gethostbyname, tmp_path):
        """URL hosts, ports, and brackets should be cleaned before matching policies"""
        audit_log = tmp_path / "audit.log"
        engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
        engine.add_allow_rule("93.184.216.34/32", reason="Example IP")

        mock_gethostbyname.return_value = "93.184.216.34"

        # Check full URL
        allowed, reason, policy = engine.check_access(
            dest_ip="https://example.com/path?query=1",
            plugin_id="test",
        )
        assert allowed
        mock_gethostbyname.assert_called_with("example.com")

        # Check host with port
        allowed, reason, policy = engine.check_access(
            dest_ip="example.com:8080",
            plugin_id="test",
        )
        assert allowed

        # Check IPv6 brackets cleaning
        engine.add_allow_rule("::1/128", reason="IPv6 Loopback")
        allowed, reason, policy = engine.check_access(
            dest_ip="[::1]",
            plugin_id="test",
        )
        assert allowed

class TestDefaultDenylistSSRFProtection:
    """Test that private subnets are blocked by default in settings"""

    def test_private_subnets_in_default_denylist(self):
        """Standard private ranges (RFC1918, RFC6598, IPv6 local) must be in the default denylist"""
        from backend.secuscan.config import Settings
        default_settings = Settings()
        denylist = default_settings.network_denylist
        assert "10.0.0.0/8" in denylist
        assert "172.16.0.0/12" in denylist
        assert "192.168.0.0/16" in denylist
        assert "100.64.0.0/10" in denylist
        assert "fc00::/7" in denylist
        assert "fe80::/10" in denylist
        assert "::1/128" in denylist

def test_check_access_logs_url_parse_failure(caplog, tmp_path):
    engine = NetworkPolicyEngine(audit_log_path=str(tmp_path / "audit.log"))

    with patch("urllib.parse.urlparse", side_effect=RuntimeError("boom")):
        with caplog.at_level("DEBUG"):
            engine.check_access(
                dest_ip="http://example.com",
                plugin_id="test",
            )

    assert "Failed to parse URL while normalizing network policy target" in caplog.text


def test_validate_egress_target_logs_url_parse_failure(caplog, tmp_path):
    engine = NetworkPolicyEngine(audit_log_path=str(tmp_path / "audit.log"))

    with patch("backend.secuscan.network_policy.urlparse", side_effect=RuntimeError("boom")):
        with caplog.at_level("DEBUG"):
            engine.validate_egress_target("http://example.com")

    assert "Failed to parse egress target" in caplog.text
