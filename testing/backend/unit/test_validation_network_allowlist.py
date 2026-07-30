"""
Unit tests for backend.secuscan.validation._net_within_allowed_networks.

Covers exact CIDR matches, wildcard-style patterns (e.g. "10.*.*.*"),
single-IP vs multi-address networks, IPv4/IPv6 version mismatches, and
malformed wildcard patterns.
"""

import ipaddress

import pytest

from backend.secuscan.validation import _net_within_allowed_networks
from backend.secuscan.config import settings


def _set_allowed_networks(monkeypatch, patterns):
    monkeypatch.setattr(settings, "allowed_networks", patterns)


class TestNetWithinAllowedNetworks:
    def test_empty_allowlist_allows_everything(self, monkeypatch):
        """When allowed_networks is empty, any network is permitted."""
        _set_allowed_networks(monkeypatch, [])
        net = ipaddress.ip_network("8.8.8.8/32")
        assert _net_within_allowed_networks(net) is True

    def test_none_allowlist_allows_everything(self, monkeypatch):
        """When allowed_networks is None, any network is permitted."""
        _set_allowed_networks(monkeypatch, None)
        net = ipaddress.ip_network("8.8.8.8/32")
        assert _net_within_allowed_networks(net) is True

    def test_single_ip_matches_exact_cidr(self, monkeypatch):
        """A single IP inside an allowed CIDR range is permitted."""
        _set_allowed_networks(monkeypatch, ["10.0.0.0/8"])
        net = ipaddress.ip_network("10.1.2.3/32")
        assert _net_within_allowed_networks(net) is True

    def test_single_ip_outside_cidr_is_rejected(self, monkeypatch):
        """A single IP outside every allowed CIDR range is rejected."""
        _set_allowed_networks(monkeypatch, ["10.0.0.0/8"])
        net = ipaddress.ip_network("192.168.1.1/32")
        assert _net_within_allowed_networks(net) is False

    def test_single_ip_matches_wildcard_pattern(self, monkeypatch):
        """A single IP matching a trailing-octet wildcard is permitted."""
        _set_allowed_networks(monkeypatch, ["10.*.*.*"])
        net = ipaddress.ip_network("10.5.5.5/32")
        assert _net_within_allowed_networks(net) is True

    def test_single_ip_matches_partial_wildcard(self, monkeypatch):
        """A wildcard with only the last two octets wildcarded still matches correctly."""
        _set_allowed_networks(monkeypatch, ["10.20.*.*"])
        net = ipaddress.ip_network("10.20.30.40/32")
        assert _net_within_allowed_networks(net) is True

    def test_single_ip_fails_partial_wildcard_wrong_prefix(self, monkeypatch):
        """A partial wildcard does not match an IP outside its fixed prefix."""
        _set_allowed_networks(monkeypatch, ["10.20.*.*"])
        net = ipaddress.ip_network("10.21.30.40/32")
        assert _net_within_allowed_networks(net) is False

    def test_malformed_wildcard_digit_after_star_is_ignored(self, monkeypatch):
        """A pattern like '10.*.5.*' (digit after a wildcard octet) can't convert to
        a CIDR and isn't a valid IP network, so it falls back to fnmatch — a target
        that doesn't literally match the glob is rejected."""
        _set_allowed_networks(monkeypatch, ["10.*.5.*"])
        net = ipaddress.ip_network("10.1.5.9/32")
        # wildcard_to_net returns None for this shape, so this exercises the
        # fnmatch(ip_str, pattern) fallback path instead.
        assert _net_within_allowed_networks(net) is True

    def test_malformed_wildcard_no_fnmatch_hit_is_rejected(self, monkeypatch):
        """A malformed wildcard pattern that also doesn't fnmatch the target is rejected."""
        _set_allowed_networks(monkeypatch, ["10.*.5.*"])
        net = ipaddress.ip_network("10.1.6.9/32")
        assert _net_within_allowed_networks(net) is False

    def test_out_of_range_octet_pattern_is_skipped(self, monkeypatch):
        """A pattern with an out-of-range octet (e.g. 999) is neither a valid
        ip_network nor a valid wildcard, so it's effectively skipped."""
        _set_allowed_networks(monkeypatch, ["999.0.0.0/8"])
        net = ipaddress.ip_network("10.0.0.1/32")
        assert _net_within_allowed_networks(net) is False

    def test_ipv4_target_ignores_ipv6_allowlist_entry(self, monkeypatch):
        """An IPv6-only allowlist entry never matches an IPv4 target."""
        _set_allowed_networks(monkeypatch, ["::1/128"])
        net = ipaddress.ip_network("127.0.0.1/32")
        assert _net_within_allowed_networks(net) is False

    def test_ipv6_target_matches_ipv6_allowlist_entry(self, monkeypatch):
        """An IPv6 target matches an IPv6 CIDR entry of the same version."""
        _set_allowed_networks(monkeypatch, ["::1/128"])
        net = ipaddress.ip_network("::1/128")
        assert _net_within_allowed_networks(net) is True

    def test_multi_address_network_fully_inside_allowed_cidr(self, monkeypatch):
        """A multi-address network fully contained in an allowed CIDR is permitted."""
        _set_allowed_networks(monkeypatch, ["10.0.0.0/8"])
        net = ipaddress.ip_network("10.1.0.0/24")
        assert _net_within_allowed_networks(net) is True

    def test_multi_address_network_partially_overlapping_is_rejected(self, monkeypatch):
        """A multi-address network that only overlaps (rather than fully fits inside)
        an allowed CIDR is rejected — multi-address targets require full containment."""
        _set_allowed_networks(monkeypatch, ["10.0.0.0/24"])
        wider_net = ipaddress.ip_network("10.0.0.0/23")
        assert _net_within_allowed_networks(wider_net) is False

    def test_multi_address_network_matches_wildcard_allowlist(self, monkeypatch):
        """A multi-address network fully inside a wildcard-derived CIDR is permitted."""
        _set_allowed_networks(monkeypatch, ["10.*.*.*"])
        net = ipaddress.ip_network("10.5.0.0/16")
        assert _net_within_allowed_networks(net) is True

    def test_multi_address_network_no_matching_entry_is_rejected(self, monkeypatch):
        """A multi-address network with no allowlist entry containing it is rejected."""
        _set_allowed_networks(monkeypatch, ["10.0.0.0/8"])
        net = ipaddress.ip_network("172.16.0.0/16")
        assert _net_within_allowed_networks(net) is False

    def test_multiple_allowlist_entries_first_non_matching_second_matching(self, monkeypatch):
        """When multiple allowlist entries exist, a match on any one of them is enough."""
        _set_allowed_networks(monkeypatch, ["192.168.0.0/16", "10.0.0.0/8"])
        net = ipaddress.ip_network("10.5.5.5/32")
        assert _net_within_allowed_networks(net) is True