"""
Unit tests for _net_within_allowed_networks helper in
backend/secuscan/validation.py.

The _net_within_allowed_networks function checks whether a given network
is permitted by settings.allowed_networks. It is a conservative gate:
if the allowlist is empty, all networks are permitted (returns True);
if the allowlist has entries, only explicitly allowed networks pass.

This function is a pure decision-making helper — it does not mutate state,
does not access the DB, and does not need the full FastAPI stack.
Tests run with --noconftest (no heavy backend imports needed).
"""

import ipaddress
import pytest
from unittest.mock import patch


def _net_within_allowed_networks(net: ipaddress._BaseNetwork) -> bool:
    """Thin wrapper to enable direct unit testing without importing settings."""
    from backend.secuscan.validation import _net_within_allowed_networks as _fn
    return _fn(net)


class TestAllowlistEmpty:
    """When allowed_networks is empty or None, all non-blocked networks pass."""

    def test_single_ip_allowed_when_no_allowlist(self):
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = []
            net = ipaddress.ip_network("8.8.8.8/32")
            assert _net_within_allowed_networks(net) is True

    def test_private_network_allowed_when_no_allowlist(self):
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = None
            net = ipaddress.ip_network("10.0.0.0/8")
            assert _net_within_allowed_networks(net) is True

    def test_public_network_allowed_when_no_allowlist(self):
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = []
            net = ipaddress.ip_network("1.2.3.4/24")
            assert _net_within_allowed_networks(net) is True


class TestExplicitAllowlist:
    """When an allowlist is configured, only explicitly allowed networks pass."""

    def test_explicit_cidr_allowed(self):
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = ["10.0.0.0/8"]
            net = ipaddress.ip_network("10.1.2.3/32")
            assert _net_within_allowed_networks(net) is True

    def test_public_ip_denied_when_only_private_allowed(self):
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = ["10.0.0.0/8"]
            net = ipaddress.ip_network("8.8.8.8/32")
            assert _net_within_allowed_networks(net) is False

    def test_smaller_subnet_denied_when_larger_allowed(self):
        """Only the exact allowed CIDR passes; a different CIDR is denied."""
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = ["192.168.0.0/16"]
            net = ipaddress.ip_network("10.0.0.0/8")
            assert _net_within_allowed_networks(net) is False

    def test_allowed_network_includes_network_address(self):
        """The network address itself (e.g. 192.168.1.0/24) is included in the subnet."""
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = ["192.168.1.0/24"]
            net = ipaddress.ip_network("192.168.1.0/24")
            assert _net_within_allowed_networks(net) is True

    def test_whitespace_in_pattern_stripped(self):
        """Patterns with leading/trailing whitespace are stripped before use."""
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = ["  10.0.0.0/8  ", " 192.168.0.0/16 "]
            net = ipaddress.ip_network("192.168.5.5/32")
            assert _net_within_allowed_networks(net) is True

    def test_empty_patterns_ignored(self):
        """Empty/whitespace-only patterns in the list are ignored."""
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = ["10.0.0.0/8", "  ", ""]
            net = ipaddress.ip_network("8.8.8.8/32")
            assert _net_within_allowed_networks(net) is False


class TestMultiAddressNetworks:
    """Multi-address (CIDR) networks: only explicit CIDR allowlist entries pass."""

    def test_multi_address_network_allowed_by_exact_cidr(self):
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = ["10.0.0.0/8"]
            net = ipaddress.ip_network("10.0.0.0/8")
            assert _net_within_allowed_networks(net) is True

    def test_multi_address_network_denied_when_not_in_allowlist(self):
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = ["10.0.0.0/8"]
            net = ipaddress.ip_network("192.168.0.0/16")
            assert _net_within_allowed_networks(net) is False

    def test_multi_address_network_allowed_when_supernet_in_allowlist(self):
        """A /24 network is allowed if its containing /16 is in the allowlist."""
        with patch("backend.secuscan.validation.settings") as mock_settings:
            mock_settings.allowed_networks = ["192.168.0.0/16"]
            net = ipaddress.ip_network("192.168.1.0/24")
            assert _net_within_allowed_networks(net) is True
