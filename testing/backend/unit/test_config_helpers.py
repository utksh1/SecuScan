"""Tests for config.py module-level constants."""

import pytest

from backend.secuscan.config import MANDATORY_DENYLIST


class TestMandatoryDenylistStructure:
    """MANDATORY_DENYLIST must be a non-empty, well-formed list of CIDR ranges."""

    def test_denylist_is_non_empty(self):
        assert MANDATORY_DENYLIST
        assert len(MANDATORY_DENYLIST) > 0

    def test_all_entries_are_strings(self):
        for entry in MANDATORY_DENYLIST:
            assert isinstance(entry, str), f"Expected str, got {type(entry).__name__}: {entry}"

    def test_no_empty_entries(self):
        for entry in MANDATORY_DENYLIST:
            assert entry.strip(), f"Empty entry found in MANDATORY_DENYLIST"

    def test_all_entries_look_like_cidr_ranges(self):
        for entry in MANDATORY_DENYLIST:
            # Must contain a slash separating prefix from prefix length
            assert "/" in entry, f"No slash in CIDR entry: {entry}"
            parts = entry.split("/")
            assert len(parts) == 2, f"Invalid CIDR format: {entry}"
            prefix, prefix_len = parts
            assert prefix, f"Empty prefix in CIDR entry: {entry}"
            assert prefix_len.isdigit(), f"Non-numeric prefix length in: {entry}"


class TestMandatoryDenylistCoverage:
    """Critical security ranges must be present in MANDATORY_DENYLIST."""

    def test_cloud_metadata_169_254_present(self):
        """AWS/GCP/Azure/OCI instance metadata endpoint must be blocked."""
        assert "169.254.169.254/32" in MANDATORY_DENYLIST

    def test_link_local_metadata_range_present(self):
        """169.254.0.0/16 link-local range must be blocked."""
        assert "169.254.0.0/16" in MANDATORY_DENYLIST

    def test_loopback_present(self):
        """127.0.0.0/8 loopback range must be blocked."""
        assert "127.0.0.0/8" in MANDATORY_DENYLIST

    def test_rfc1918_10_private_present(self):
        """10.0.0.0/8 RFC1918 private range must be blocked."""
        assert "10.0.0.0/8" in MANDATORY_DENYLIST

    def test_rfc1918_172_private_present(self):
        """172.16.0.0/12 RFC1918 private range must be blocked."""
        assert "172.16.0.0/12" in MANDATORY_DENYLIST

    def test_rfc1918_192_private_present(self):
        """192.168.0.0/16 RFC1918 private range must be blocked."""
        assert "192.168.0.0/16" in MANDATORY_DENYLIST

    def test_cgnat_range_present(self):
        """100.64.0.0/10 carrier-grade NAT range must be blocked."""
        assert "100.64.0.0/10" in MANDATORY_DENYLIST

    def test_ipv6_unique_local_present(self):
        """fc00::/7 IPv6 unique local address range must be blocked."""
        assert "fc00::/7" in MANDATORY_DENYLIST

    def test_ipv6_link_local_present(self):
        """fe80::/10 IPv6 link-local address range must be blocked."""
        assert "fe80::/10" in MANDATORY_DENYLIST

    def test_ipv6_loopback_present(self):
        """::1/128 IPv6 loopback must be blocked."""
        assert "::1/128" in MANDATORY_DENYLIST


class TestMandatoryDenylistIPv4:
    """IPv4 ranges must be valid and parseable."""

    def test_ipv4_entries_parse_without_error(self):
        import ipaddress
        for entry in MANDATORY_DENYLIST:
            if ":" not in entry:  # IPv4 entries do not contain colons
                try:
                    ipaddress.ip_network(entry, strict=False)
                except ValueError as exc:
                    pytest.fail(f"Invalid IPv4 CIDR {entry}: {exc}")

    def test_ipv4_entries_cover_expected_subnets(self):
        import ipaddress
        # Verify each IPv4 entry is a valid network
        ipv4_entries = [e for e in MANDATORY_DENYLIST if ":" not in e]
        assert len(ipv4_entries) >= 6, "Expected at least 6 IPv4 ranges"


class TestMandatoryDenylistIPv6:
    """IPv6 ranges must be valid and parseable."""

    def test_ipv6_entries_parse_without_error(self):
        import ipaddress
        for entry in MANDATORY_DENYLIST:
            if ":" in entry:  # IPv6 entries contain colons
                try:
                    ipaddress.ip_network(entry, strict=False)
                except ValueError as exc:
                    pytest.fail(f"Invalid IPv6 CIDR {entry}: {exc}")

    def test_ipv6_entries_cover_expected_subnets(self):
        ipv6_entries = [e for e in MANDATORY_DENYLIST if ":" in e]
        assert len(ipv6_entries) >= 3, "Expected at least 3 IPv6 ranges"


class TestMandatoryDenylistNoDuplicates:
    """MANDATORY_DENYLIST must not contain duplicate entries."""

    def test_no_duplicate_entries(self):
        seen = set()
        for entry in MANDATORY_DENYLIST:
            assert entry not in seen, f"Duplicate entry found: {entry}"
            seen.add(entry)
