"""
Unit tests for PolicyAction enum and dataclass to_dict() serialization
contracts in backend/secuscan/network_policy.py.

Tests meaningful serialization contracts and JSON round-trip behavior
for NetworkPolicy and AuditLogEntry.
"""

import json

import pytest
from datetime import datetime, timezone

from backend.secuscan.network_policy import (
    PolicyAction,
    NetworkPolicy,
    AuditLogEntry,
)


class TestPolicyActionEnum:
    """Minimal enum coverage focused on behavior."""

    def test_policy_action_members_are_valid_strings(self):
        """Each PolicyAction member serialises to a non-empty lowercase string."""
        for member in PolicyAction:
            assert isinstance(member.value, str)
            assert member.value
            assert member.value == member.value.lower()


class TestNetworkPolicyToDict:
    """Meaningful serialization contract tests for NetworkPolicy.to_dict()."""

    def test_returns_all_expected_keys(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="10.0.0.0/8",
            action=PolicyAction.ALLOW,
            reason="internal network",
            created_at=now,
        )
        result = policy.to_dict()
        assert set(result.keys()) == {
            "cidr",
            "action",
            "reason",
            "created_at",
            "expires_at",
        }

    def test_action_serialised_as_lowercase_string(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="0.0.0.0/8",
            action=PolicyAction.DENY,
            reason="blocked",
            created_at=now,
        )
        result = policy.to_dict()
        assert isinstance(result["action"], str)
        assert result["action"] == "deny"

    def test_expires_at_none_when_not_set(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="10.0.0.0/8",
            action=PolicyAction.ALLOW,
            reason="test",
            created_at=now,
        )
        result = policy.to_dict()
        assert result["expires_at"] is None

    def test_expires_at_iso_string_when_set(self):
        now = datetime.now(timezone.utc)
        expires = datetime(2030, 1, 1, tzinfo=timezone.utc)
        policy = NetworkPolicy(
            cidr="10.0.0.0/8",
            action=PolicyAction.ALLOW,
            reason="test",
            created_at=now,
            expires_at=expires,
        )
        result = policy.to_dict()
        assert result["expires_at"] is not None
        assert "2030-01-01" in result["expires_at"]

    def test_cidr_and_reason_preserved(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="192.168.1.0/24",
            action=PolicyAction.DENY,
            reason="internal",
            created_at=now,
        )
        result = policy.to_dict()
        assert result["cidr"] == "192.168.1.0/24"
        assert result["reason"] == "internal"

    def test_json_roundtrip(self):
        """NetworkPolicy.to_dict() round-trips cleanly through JSON."""
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="10.0.0.0/8",
            action=PolicyAction.ALLOW,
            reason="internal network",
            created_at=now,
        )
        result = policy.to_dict()
        serialized = json.dumps(result)
        restored = json.loads(serialized)
        assert restored["cidr"] == "10.0.0.0/8"
        assert restored["action"] == "allow"
        assert restored["reason"] == "internal network"
        assert restored["expires_at"] is None


class TestAuditLogEntryToDict:
    """Meaningful serialization contract tests for AuditLogEntry.to_dict()."""

    def test_returns_all_expected_keys(self):
        now = datetime.now(timezone.utc)
        entry = AuditLogEntry(
            timestamp=now,
            plugin_id="test_plugin",
            task_id="task-123",
            action=PolicyAction.ALLOW,
            dest_ip="8.8.8.8",
            dest_port=53,
            dest_hostname="dns.google",
            policy_matched="0.0.0.0/0",
            reason="allowed",
        )
        result = entry.to_dict()
        expected_keys = {
            "timestamp",
            "plugin_id",
            "task_id",
            "action",
            "dest_ip",
            "dest_port",
            "dest_hostname",
            "policy_matched",
            "reason",
        }
        assert set(result.keys()) == expected_keys

    def test_action_serialised_as_lowercase_string(self):
        now = datetime.now(timezone.utc)
        entry = AuditLogEntry(
            timestamp=now,
            plugin_id="test",
            task_id="t1",
            action=PolicyAction.DENY,
            dest_ip="169.254.0.1",
            dest_port=80,
            dest_hostname=None,
            policy_matched="169.254.0.0/16",
            reason="blocked",
        )
        result = entry.to_dict()
        assert result["action"] == "deny"

    def test_dest_hostname_none_when_not_set(self):
        now = datetime.now(timezone.utc)
        entry = AuditLogEntry(
            timestamp=now,
            plugin_id="test",
            task_id="t1",
            action=PolicyAction.ALLOW,
            dest_ip="8.8.8.8",
            dest_port=443,
            dest_hostname=None,
            policy_matched="0.0.0.0/0",
            reason="ok",
        )
        result = entry.to_dict()
        assert result["dest_hostname"] is None

    def test_plugin_id_preserved(self):
        now = datetime.now(timezone.utc)
        entry = AuditLogEntry(
            timestamp=now,
            plugin_id="my-scanner-plugin",
            task_id="t1",
            action=PolicyAction.ALLOW,
            dest_ip="1.1.1.1",
            dest_port=443,
            dest_hostname=None,
            policy_matched="0.0.0.0/0",
            reason="ok",
        )
        result = entry.to_dict()
        assert result["plugin_id"] == "my-scanner-plugin"

    def test_json_roundtrip(self):
        """AuditLogEntry.to_dict() round-trips cleanly through JSON."""
        now = datetime.now(timezone.utc)
        entry = AuditLogEntry(
            timestamp=now,
            plugin_id="test_plugin",
            task_id="task-123",
            action=PolicyAction.ALLOW,
            dest_ip="8.8.8.8",
            dest_port=53,
            dest_hostname="dns.google",
            policy_matched="0.0.0.0/0",
            reason="allowed",
        )
        result = entry.to_dict()
        serialized = json.dumps(result)
        restored = json.loads(serialized)
        assert restored["plugin_id"] == "test_plugin"
        assert restored["dest_ip"] == "8.8.8.8"
        assert restored["action"] == "allow"
        assert restored["dest_hostname"] == "dns.google"
