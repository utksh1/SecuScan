"""
Unit tests for PolicyAction enum values and dataclass to_dict() methods in
backend/secuscan/network_policy.py.

The to_dict() methods are used to serialize audit log entries and policy rules
for JSON logging and API responses.
"""

import pytest
from datetime import datetime, timezone

from backend.secuscan.network_policy import (
    PolicyAction,
    NetworkPolicy,
    AuditLogEntry,
)


class TestPolicyActionEnum:
    def test_allow_value(self):
        assert PolicyAction.ALLOW.value == "allow"

    def test_deny_value(self):
        assert PolicyAction.DENY.value == "deny"

    def test_member_count(self):
        assert len(PolicyAction) == 2

    def test_allow_is_policy_action(self):
        assert isinstance(PolicyAction.ALLOW, PolicyAction)

    def test_deny_is_policy_action(self):
        assert isinstance(PolicyAction.DENY, PolicyAction)


class TestNetworkPolicyToDict:
    def test_returns_all_expected_keys(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="10.0.0.0/8",
            action=PolicyAction.ALLOW,
            reason="internal network",
            created_at=now,
        )
        result = policy.to_dict()
        assert "cidr" in result
        assert "action" in result
        assert "reason" in result
        assert "created_at" in result
        assert "expires_at" in result

    def test_action_serialized_as_string(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="10.0.0.0/8",
            action=PolicyAction.ALLOW,
            reason="test",
            created_at=now,
        )
        result = policy.to_dict()
        assert isinstance(result["action"], str)
        assert result["action"] == "allow"

    def test_deny_action_serialized_as_string(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="0.0.0.0/8",
            action=PolicyAction.DENY,
            reason="blocked",
            created_at=now,
        )
        result = policy.to_dict()
        assert result["action"] == "deny"

    def test_expires_at_serialized_as_iso_string(self):
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

    def test_created_at_serialized_as_iso_string(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="10.0.0.0/8",
            action=PolicyAction.ALLOW,
            reason="test",
            created_at=now,
        )
        result = policy.to_dict()
        assert result["created_at"] is not None
        assert "T" in result["created_at"]  # ISO format

    def test_cidr_preserved(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="192.168.1.0/24",
            action=PolicyAction.DENY,
            reason="internal",
            created_at=now,
        )
        result = policy.to_dict()
        assert result["cidr"] == "192.168.1.0/24"

    def test_reason_preserved(self):
        now = datetime.now(timezone.utc)
        policy = NetworkPolicy(
            cidr="10.0.0.0/8",
            action=PolicyAction.ALLOW,
            reason="my reason text",
            created_at=now,
        )
        result = policy.to_dict()
        assert result["reason"] == "my reason text"


class TestAuditLogEntryToDict:
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

    def test_action_serialized_as_string(self):
        now = datetime.now(timezone.utc)
        entry = AuditLogEntry(
            timestamp=now,
            plugin_id="test",
            task_id="t1",
            action=PolicyAction.ALLOW,
            dest_ip="8.8.8.8",
            dest_port=80,
            dest_hostname=None,
            policy_matched="0.0.0.0/0",
            reason="ok",
        )
        result = entry.to_dict()
        assert isinstance(result["action"], str)
        assert result["action"] == "allow"

    def test_deny_action_serialized_as_string(self):
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

    def test_timestamp_serialized_as_iso_string(self):
        now = datetime.now(timezone.utc)
        entry = AuditLogEntry(
            timestamp=now,
            plugin_id="test",
            task_id="t1",
            action=PolicyAction.ALLOW,
            dest_ip="1.1.1.1",
            dest_port=443,
            dest_hostname=None,
            policy_matched="0.0.0.0/0",
            reason="ok",
        )
        result = entry.to_dict()
        assert "T" in result["timestamp"]

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
