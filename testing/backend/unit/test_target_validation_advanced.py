import pytest
import asyncio
import ipaddress
from unittest.mock import AsyncMock, patch, MagicMock
from backend.secuscan.validation import (
    validate_target,
    resolve_hostname,
)
from backend.secuscan.config import settings


@pytest.mark.asyncio
class TestDNSResolution:
    """Test DNS resolution with SSRF prevention"""

    @pytest.mark.asyncio
    async def test_public_hostname_resolves_and_passes(self):
        """Valid public hostname should resolve and pass"""
        with patch("backend.secuscan.validation.resolve_hostname", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = ["8.8.8.8"]
            is_valid, error = await validate_target(
                "google.com",
                safe_mode=False,
                resolve_dns=True
            )
            assert is_valid
            assert error == ""
            mock_resolve.assert_called_once_with("google.com", timeout=settings.dns_timeout_seconds)

    @pytest.mark.asyncio
    async def test_hostname_resolving_to_private_ip_blocked(self):
        """Hostname resolving to private IP should be blocked to prevent SSRF"""
        with patch("backend.secuscan.validation.resolve_hostname", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = ["192.168.1.1"]
            is_valid, error = await validate_target(
                "internal.corp",
                safe_mode=False,
                resolve_dns=True
            )
            assert not is_valid
            assert "resolves to blocked IP 192.168.1.1" in error

    @pytest.mark.asyncio
    async def test_hostname_resolving_to_aws_metadata_blocked(self):
        """Hostname resolving to AWS metadata endpoint (link-local) should be blocked"""
        with patch("backend.secuscan.validation.resolve_hostname", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = ["169.254.169.254"]
            is_valid, error = await validate_target(
                "aws-metadata.local",
                safe_mode=False,
                resolve_dns=True
            )
            assert not is_valid
            assert "resolves to blocked IP 169.254.169.254" in error

    @pytest.mark.asyncio
    async def test_dns_timeout_or_failure_in_safe_mode(self):
        """DNS resolution failure in safe mode should fail-closed"""
        with patch("backend.secuscan.validation.resolve_hostname", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.side_effect = Exception("DNS Resolution Timeout")
            is_valid, error = await validate_target(
                "slow-dns.example.com",
                safe_mode=True,
                resolve_dns=True
            )
            assert not is_valid
            assert "Failed to resolve hostname" in error

    @pytest.mark.asyncio
    async def test_dns_timeout_or_failure_in_permissive_mode(self):
        """DNS resolution failure in permissive mode should fail-open"""
        with patch("backend.secuscan.validation.resolve_hostname", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.side_effect = Exception("DNS Resolution Timeout")
            is_valid, error = await validate_target(
                "slow-dns.example.com",
                safe_mode=False,
                resolve_dns=True
            )
            assert is_valid
            assert error == ""


@pytest.mark.asyncio
class TestHTTPRedirects:
    """Test HTTP redirect validation"""

    @pytest.mark.asyncio
    async def test_redirect_to_public_url_allowed(self):
        """Redirect to public URL should be allowed"""
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 302
        mock_response_1.headers = {"location": "https://final-destination.com"}

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200

        with patch("httpx.AsyncClient.head") as mock_head, \
             patch("backend.secuscan.validation.resolve_hostname", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = ["8.8.8.8"]
            mock_head.side_effect = [mock_response_1, mock_response_2]

            is_valid, error = await validate_target(
                "https://short.link/123",
                safe_mode=False,
                follow_redirects=True,
                resolve_dns=True
            )
            assert is_valid
            assert error == ""

    @pytest.mark.asyncio
    async def test_redirect_to_private_ip_blocked(self):
        """Redirect to private IP should be blocked"""
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 302
        mock_response_1.headers = {"location": "http://192.168.1.1:8080"}

        with patch("httpx.AsyncClient.head") as mock_head, \
             patch("backend.secuscan.validation.resolve_hostname", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = ["8.8.8.8"]
            mock_head.return_value = mock_response_1

            is_valid, error = await validate_target(
                "https://attacker.com/redirect",
                safe_mode=False,
                follow_redirects=True,
                resolve_dns=True
            )
            assert not is_valid
            assert "Private IP ranges are blocked" in error or "Target overlaps with blocked network range" in error

    @pytest.mark.asyncio
    async def test_redirect_chain_exceeds_max_hops(self):
        """Redirect chain exceeding max hops should fail"""
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"location": "https://attacker.com/infinite"}

        with patch("httpx.AsyncClient.head", return_value=mock_response), \
             patch("backend.secuscan.validation.resolve_hostname", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = ["8.8.8.8"]

            # Use settings max hops (5)
            is_valid, error = await validate_target(
                "https://attacker.com/infinite",
                safe_mode=False,
                follow_redirects=True,
                resolve_dns=True
            )
            assert not is_valid
            assert "Redirect chain exceeded" in error


@pytest.mark.asyncio
class TestIPv6Handling:
    """Test IPv6 target validation"""

    @pytest.mark.asyncio
    async def test_ipv6_public_address_allowed_in_permissive_mode(self):
        """Public IPv6 address should be allowed in permissive mode"""
        is_valid, error = await validate_target(
            "2001:4860:4860::8888",  # Google Public DNS IPv6
            safe_mode=False
        )
        assert is_valid
        assert error == ""

    @pytest.mark.asyncio
    async def test_ipv6_loopback_blocked(self):
        """IPv6 loopback should be blocked by default unless enabled"""
        # Set loopback scans setting to false temporarily to verify
        with patch.object(settings, "allow_loopback", False), \
             patch.object(settings, "allow_loopback_scans", False):
            is_valid, error = await validate_target(
                "::1",
                safe_mode=False
            )
            assert not is_valid
            assert "Loopback scans are disabled" in error

    @pytest.mark.asyncio
    async def test_ipv6_link_local_blocked(self):
        """IPv6 link-local (fe80::/10) should be blocked"""
        is_valid, error = await validate_target(
            "fe80::1",
            safe_mode=False
        )
        assert not is_valid
        assert "blocked network range" in error


@pytest.mark.asyncio
class TestOperatorPolicies:
    """Test allowlist and denylist overrides"""

    @pytest.mark.asyncio
    async def test_allowlist_permits_private_ip(self):
        """Allowlist overrides permissive mode private IP blocking"""
        with patch.object(settings, "network_allowlist", ["10.0.0.0/8"]):
            is_valid, error = await validate_target(
                "10.5.5.5",
                safe_mode=False
            )
            assert is_valid
            assert error == ""

    @pytest.mark.asyncio
    async def test_denylist_takes_precedence_over_allowlist(self):
        """Denylist takes absolute precedence over allowlist"""
        with patch.object(settings, "network_allowlist", ["10.0.0.0/8"]), \
             patch.object(settings, "network_denylist", ["10.1.1.0/24"]):
            is_valid, error = await validate_target(
                "10.1.1.5",
                safe_mode=False
            )
            assert not is_valid
            assert "denied network range" in error

    @pytest.mark.asyncio
    async def test_safe_mode_unaffected_by_allowlist(self):
        """Safe mode still blocks public networks even if they are in allowlist"""
        with patch.object(settings, "network_allowlist", ["8.8.8.0/24"]):
            is_valid, error = await validate_target(
                "8.8.8.8",
                safe_mode=True
            )
            assert not is_valid
            assert "Public IPs/networks not allowed in safe mode" in error
