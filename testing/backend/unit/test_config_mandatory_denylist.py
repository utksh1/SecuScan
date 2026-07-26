"""
Unit tests for backend/secuscan/config.py MANDATORY_DENYLIST constant.

The MANDATORY_DENYLIST is a security-critical list of CIDR notation strings
representing IPs and networks that must never be reachable by any scanner
plugin. These tests verify the structure, validity, and completeness of the
deny-list.

Run with:
    python3 -m pytest testing/backend/unit/test_config_mandatory_denylist.py -v --noconftest
"""

from __future__ import annotations

import ipaddress
import pytest

from backend.secuscan.config import MANDATORY_DENYLIST


class TestMandatoryDenylistStructure:
    """Tests for the basic structure of MANDATORY_DENYLIST."""

    def test_is_a_non_empty_list(self):
        """MANDATORY_DENYLIST must be a non-empty list."""
        assert isinstance(MANDATORY_DENYLIST, list)
        assert len(MANDATORY_DENYLIST) > 0

    def test_all_entries_are_strings(self):
        """Every entry in MANDATORY_DENYLIST must be a string."""
        for entry in MANDATORY_DENYLIST:
            assert isinstance(entry, str), f"Entry {entry!r} is not a string"

    def test_no_none_entries(self):
        """MANDATORY_DENYLIST must not contain None values."""
        assert None not in MANDATORY_DENYLIST

    def test_no_empty_string_entries(self):
        """MANDATORY_DENYLIST must not contain empty string entries."""
        for entry in MANDATORY_DENYLIST:
            assert entry != "", f"Empty string entry found in MANDATORY_DENYLIST"


class TestMandatoryDenylistCidrValidity:
    """Tests that every entry in MANDATORY_DENYLIST is a valid CIDR string."""

    @pytest.mark.parametrize("cidr", MANDATORY_DENYLIST)
    def test_each_entry_is_valid_cidr(self, cidr):
        """Each entry must be a valid CIDR string parseable by ipaddress."""
        try:
            ipaddress.ip_network(cidr)
        except ValueError as e:
            pytest.fail(f"Invalid CIDR {cidr!r}: {e}")

    @pytest.mark.parametrize("cidr", MANDATORY_DENYLIST)
    def test_each_entry_is_strictly_valid(self, cidr):
        """Each entry must be valid when using strict=True."""
        try:
            ipaddress.ip_network(cidr, strict=True)
        except ValueError:
            pytest.fail(f"CIDR {cidr!r} is not strictly valid")


class TestMandatoryDenylistNoDuplicates:
    """Tests that MANDATORY_DENYLIST contains no duplicate entries."""

    def test_no_exact_duplicates(self):
        """MANDATORY_DENYLIST must not contain the same CIDR twice."""
        seen = set()
        duplicates = []
        for entry in MANDATORY_DENYLIST:
            normalized = str(ipaddress.ip_network(entry))
            if normalized in seen:
                duplicates.append(entry)
            seen.add(normalized)
        assert duplicates == [], f"Duplicate entries found: {duplicates}"

    def test_no_overlapping_duplicates(self):
        """MANDATORY_DENYLIST must not contain the same CIDR in different forms.

        For example, '10.0.0.0/8' and '10.0.0.0/8' (same) are caught by the
        exact-duplicate test. This test additionally catches entries that differ
        only in formatting (e.g. '10.0.0.0/8' vs '10.0.0.0/8 ' with trailing
        space, which is also caught by the string-type test above).
        """
        seen = set()
        for entry in MANDATORY_DENYLIST:
            normalized = entry.strip()
            assert normalized not in seen, f"Duplicate or near-duplicate entry: {entry!r}"
            seen.add(normalized)


class TestMandatoryDenylistExpectedEntries:
    """Tests that the expected critical entries are present in MANDATORY_DENYLIST."""

    def test_cloud_metadata_169_254_169_254(self):
        """The AWS/GCP/Azure cloud metadata endpoint 169.254.169.254 must be denied."""
        assert "169.254.169.254/32" in MANDATORY_DENYLIST

    def test_link_local_169_254_0_0_16(self):
        """The 169.254.0.0/16 link-local range must be denied."""
        assert "169.254.0.0/16" in MANDATORY_DENYLIST

    def test_loopback_127_0_0_0_8(self):
        """The IPv4 loopback range 127.0.0.0/8 must be denied."""
        assert "127.0.0.0/8" in MANDATORY_DENYLIST

    def test_rfc1918_10_0_0_0_8(self):
        """The RFC 1918 private range 10.0.0.0/8 must be denied."""
        assert "10.0.0.0/8" in MANDATORY_DENYLIST

    def test_rfc1918_172_16_0_0_12(self):
        """The RFC 1918 private range 172.16.0.0/12 must be denied."""
        assert "172.16.0.0/12" in MANDATORY_DENYLIST

    def test_rfc1918_192_168_0_0_16(self):
        """The RFC 1918 private range 192.168.0.0/16 must be denied."""
        assert "192.168.0.0/16" in MANDATORY_DENYLIST

    def test_cgnat_100_64_0_0_10(self):
        """The CGNAT range 100.64.0.0/10 (RFC 6598) must be denied."""
        assert "100.64.0.0/10" in MANDATORY_DENYLIST

    def test_ipv6_loopback(self):
        """The IPv6 loopback address ::1/128 must be denied."""
        assert "::1/128" in MANDATORY_DENYLIST

    def test_ipv6_link_local(self):
        """The IPv6 link-local range fe80::/10 must be denied."""
        assert "fe80::/10" in MANDATORY_DENYLIST

    def test_ipv6_ula(self):
        """The IPv6 Unique Local Address range fc00::/7 must be denied."""
        assert "fc00::/7" in MANDATORY_DENYLIST


class TestMandatoryDenylistImportability:
    """Tests that MANDATORY_DENYLIST is properly importable as a module constant."""

    def test_importable_from_config(self):
        """MANDATORY_DENYLIST must be importable from backend.secuscan.config."""
        from backend.secuscan.config import MANDATORY_DENYLIST as imported
        assert isinstance(imported, list)
        assert len(imported) > 0
