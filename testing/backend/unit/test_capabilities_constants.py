"""
Unit tests for Capability enum values and ALL_CAPABILITIES constant in
backend/secuscan/capabilities.py.

These are the authoritative single source of truth for all supported
capability tokens. Direct unit tests catch drift and typos in enum definitions.
"""

import pytest

from backend.secuscan.capabilities import Capability, ALL_CAPABILITIES


class TestCapabilityEnum:
    def test_network_value(self):
        assert Capability.NETWORK.value == "network"

    def test_filesystem_value(self):
        assert Capability.FILESYSTEM.value == "filesystem"

    def test_docker_value(self):
        assert Capability.DOCKER.value == "docker"

    def test_credentials_value(self):
        assert Capability.CREDENTIALS.value == "credentials"

    def test_intrusive_value(self):
        assert Capability.INTRUSIVE.value == "intrusive"

    def test_exploit_value(self):
        assert Capability.EXPLOIT.value == "exploit"

    def test_member_count(self):
        assert len(Capability) == 6

    def test_all_values_are_non_empty_strings(self):
        for member in Capability:
            assert isinstance(member.value, str)
            assert len(member.value) > 0

    def test_all_values_are_lowercase(self):
        for member in Capability:
            assert member.value == member.value.lower()

    def test_no_duplicate_values(self):
        values = [m.value for m in Capability]
        assert len(values) == len(set(values))


class TestALLCapabilities:
    def test_is_frozenset(self):
        assert isinstance(ALL_CAPABILITIES, frozenset)

    def test_is_not_list(self):
        assert not isinstance(ALL_CAPABILITIES, list)

    def test_is_not_set(self):
        assert not isinstance(ALL_CAPABILITIES, set)

    def test_has_six_members(self):
        assert len(ALL_CAPABILITIES) == 6

    def test_contains_network(self):
        assert "network" in ALL_CAPABILITIES

    def test_contains_filesystem(self):
        assert "filesystem" in ALL_CAPABILITIES

    def test_contains_docker(self):
        assert "docker" in ALL_CAPABILITIES

    def test_contains_credentials(self):
        assert "credentials" in ALL_CAPABILITIES

    def test_contains_intrusive(self):
        assert "intrusive" in ALL_CAPABILITIES

    def test_contains_exploit(self):
        assert "exploit" in ALL_CAPABILITIES

    def test_equals_frozenset_of_enum_values(self):
        expected = frozenset(c.value for c in Capability)
        assert ALL_CAPABILITIES == expected

    def test_all_members_are_non_empty_lowercase_strings(self):
        for cap in ALL_CAPABILITIES:
            assert isinstance(cap, str)
            assert len(cap) > 0
            assert cap == cap.lower()

    def test_no_duplicate_values(self):
        assert len(ALL_CAPABILITIES) == len(set(ALL_CAPABILITIES))
