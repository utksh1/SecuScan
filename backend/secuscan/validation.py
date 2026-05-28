"""
Input validation and security checks
"""

import re
import ipaddress
import logging
import asyncio
from typing import Any, Dict, Tuple, List, Optional
from fnmatch import fnmatch

from .config import settings

logger = logging.getLogger(__name__)

# Blocked network ranges (RFC 5735, RFC 6890, RFC 1122, RFC 3927)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),           # This network
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local IPv4
    ipaddress.ip_network("192.0.2.0/24"),        # TEST-NET-1
    ipaddress.ip_network("198.18.0.0/15"),       # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),     # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),      # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),         # Multicast
    ipaddress.ip_network("240.0.0.0/4"),         # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Limited Broadcast
    # IPv6 Special-Use Ranges (RFC 5156, RFC 4291)
    ipaddress.ip_network("fe80::/10"),           # Link-local IPv6
    ipaddress.ip_network("ff00::/8"),            # Multicast IPv6
]

# Allowed private IP ranges (RFC 1918)
ALLOWED_PRIVATE = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
]

# Blocked TLDs in safe mode
BLOCKED_TLDS = [".mil", ".gov"]


def _parse_network(cidr: str) -> Optional[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Helper to parse a CIDR string safely without strict boundaries."""
    try:
        return ipaddress.ip_network(cidr.strip(), strict=False)
    except ValueError:
        return None


def _validate_ip_network(net: ipaddress.IPv4Network | ipaddress.IPv6Network, safe_mode: bool) -> Tuple[bool, str]:
    """Validate a network range (or single IP) against all active policies."""
    # Check loopback (IPv4/IPv6 loopback)
    is_loopback = net.is_loopback or net.overlaps(ipaddress.ip_network("127.0.0.0/8")) or net.overlaps(ipaddress.ip_network("::1/128"))

    # Check private networks
    is_private = any(
        (net.version == pvt.version and (net.subnet_of(pvt) or net.overlaps(pvt)))
        for pvt in ALLOWED_PRIVATE
    )

    # Safe mode check: public IPs/networks are never allowed under safe mode, even if in allowlist!
    if safe_mode and not is_private and not is_loopback:
        return False, "Public IPs/networks not allowed in safe mode (SecuScan Guardrail)"

    # 1. Check explicit denylist first (highest priority)
    denied_cidrs = [_parse_network(c) for c in settings.network_denylist if c]
    for denied in denied_cidrs:
        if denied and net.overlaps(denied):
            return False, "Target overlaps with denied network range"

    # 2. Check explicit allowlist
    allowed_cidrs = [_parse_network(c) for c in settings.network_allowlist if c]
    for allowed in allowed_cidrs:
        if allowed and net.subnet_of(allowed):
            return True, ""

    # 3. Check loopback setting
    if is_loopback:
        allow_lb = settings.allow_loopback and settings.allow_loopback_scans
        if not allow_lb:
            return False, "Loopback scans are disabled in global settings"
        return True, ""

    # 4. Check system blocked networks
    for blocked in BLOCKED_NETWORKS:
        if net.overlaps(blocked):
            return False, "Target overlaps with blocked network range"

    # 5. Check private networks permission
    if is_private:
        if safe_mode:
            return True, ""
        else:
            if settings.allow_private_ips:
                return True, ""
            else:
                return False, "Private IP ranges are blocked in permissive mode unless explicitly allowed"

    return True, ""


async def resolve_hostname(hostname: str, timeout: int = 2) -> List[str]:
    """Resolve a hostname to IP addresses with timeout protection."""
    # pyrefly: ignore [missing-import]
    import dns.resolver

    ips = []
    loop = asyncio.get_event_loop()

    for record_type in ('A', 'AAAA'):
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = float(timeout)
            resolver.lifetime = float(timeout)

            answer = await loop.run_in_executor(None, resolver.resolve, hostname, record_type)
            ips.extend([str(rdata) for rdata in answer])
        except Exception:
            pass

    return list(set(ips))


def _log_blocked_target(target: str, reason: str) -> None:
    """Log a blocked target to the audit log."""
    if not settings.log_blocked_targets:
        return

    import json
    from datetime import datetime
    import os
    
    log_file = settings.blocked_target_log_file
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "target": target,
            "reason": reason
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to blocked targets log: {e}")


async def validate_target(
    target: str,
    safe_mode: bool = True,
    resolve_dns: bool = True,
    follow_redirects: bool = True,
    allowed_networks: Optional[List[str]] = None,
    denied_networks: Optional[List[str]] = None,
    _redirect_depth: int = 0
) -> Tuple[bool, str]:
    """
    Validate scan target address (IP, Hostname, URL, or CIDR) asynchronously.
    """
    is_valid, reason = await _validate_target_internal(
        target, safe_mode, resolve_dns, follow_redirects, allowed_networks, denied_networks, _redirect_depth
    )
    if not is_valid and _redirect_depth == 0:
        _log_blocked_target(target, reason)
    return is_valid, reason


async def _validate_target_internal(
    target: str,
    safe_mode: bool,
    resolve_dns: bool,
    follow_redirects: bool,
    allowed_networks: Optional[List[str]],
    denied_networks: Optional[List[str]],
    _redirect_depth: int
) -> Tuple[bool, str]:
    target = target.strip()
    if not target:
        return False, "Target cannot be empty"

    # Try parsing as IP network (handles single IP and CIDR)
    try:
        net = ipaddress.ip_network(target, strict=False)
        return _validate_ip_network(net, safe_mode)
    except ValueError:
        # Not a direct IP address or network, treat as hostname or URL
        pass

    # Extract hostname
    hostname_to_validate = target
    if target.startswith(("http://", "https://")):
        host_part = target.split("://", 1)[1].split("/", 1)[0]
        if host_part.startswith("["):
            hostname_to_validate = host_part.split("]")[0][1:]
        else:
            hostname_to_validate = host_part.split(":", 1)[0]

    # Validate hostname format (RFC 1123)
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', hostname_to_validate):
        return False, "Invalid hostname format"

    # Check blocked TLDs in safe mode
    if safe_mode:
        for tld in BLOCKED_TLDS:
            if hostname_to_validate.lower().endswith(tld):
                return False, f"Domains ending in {tld} are blocked in safe mode"

    # Check if the extracted hostname is actually a literal IP address!
    is_literal_ip = False
    try:
        ip_net = ipaddress.ip_network(hostname_to_validate, strict=False)
        is_literal_ip = True
        is_valid, reason = _validate_ip_network(ip_net, safe_mode)
        if not is_valid:
            return False, reason
    except ValueError:
        pass

    # DNS Resolution Check (only if not a literal IP)
    if not is_literal_ip and resolve_dns and settings.resolve_hostname_before_scan:
        try:
            resolved_ips = await resolve_hostname(hostname_to_validate, timeout=settings.dns_timeout_seconds)
            if resolved_ips:
                for ip_str in resolved_ips:
                    try:
                        ip_net = ipaddress.ip_network(ip_str, strict=False)
                        is_valid, reason = _validate_ip_network(ip_net, safe_mode)
                        if not is_valid:
                            return False, f"Hostname '{hostname_to_validate}' resolves to blocked IP {ip_str}: {reason}"
                    except ValueError:
                        continue
            else:
                # No IPs returned
                if safe_mode:
                    return False, "Failed to resolve hostname"
        except Exception as e:
            if safe_mode:
                return False, "Failed to resolve hostname"
            else:
                logger.warning(f"DNS resolution failed for {hostname_to_validate}: {e}")

    # Follow redirects if target is URL
    if target.startswith(("http://", "https://")) and follow_redirects:
        max_hops = settings.max_redirect_hops
        if _redirect_depth >= max_hops:
            return False, f"Redirect chain exceeded maximum of {max_hops} hops"

        try:
            # pyrefly: ignore [missing-import]
            import httpx
            from urllib.parse import urljoin
            
            # HEAD request with manual redirect following
            async with httpx.AsyncClient(follow_redirects=False, timeout=3.0) as client:
                response = await client.head(target)
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if location:
                        redirect_url = urljoin(target, location)
                        # Recursively validate the redirect URL
                        return await validate_target(
                            redirect_url,
                            safe_mode=safe_mode,
                            resolve_dns=resolve_dns,
                            follow_redirects=follow_redirects,
                            allowed_networks=allowed_networks,
                            denied_networks=denied_networks,
                            _redirect_depth=_redirect_depth + 1
                        )
        except Exception as e:
            # Failed to follow redirect, log and continue as original target was valid
            logger.warning(f"Failed to follow redirect for {target}: {e}")

    return True, ""



def validate_port(port: int) -> Tuple[bool, str]:
    """
    Validate port number.

    Args:
        port: Port number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(port, int) or isinstance(port, bool):
        return False, "Port must be an integer"
    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535"
    return True, ""


def validate_port_range(port_range: str) -> Tuple[bool, str]:
    """
    Validate port range specification.

    Supports three formats:
      - Single port:              "80"
      - Hyphen range:             "1-1000"
      - Comma-separated (mixed):  "22,80,443-8080"

    Mixed comma+range specs (nmap-style) are fully supported.

    Args:
        port_range: Port range string

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Handle comma-separated ports (supports mixed specs like "80,443-8080")
    if ',' in port_range:
        for port_str in port_range.split(','):
            port_str = port_str.strip()
            if '-' in port_str:
                # Delegate sub-ranges like "443-8080" to the range parser below
                is_valid, msg = validate_port_range(port_str)
                if not is_valid:
                    return False, msg
            else:
                try:
                    port = int(port_str)
                    is_valid, msg = validate_port(port)
                    if not is_valid:
                        return False, msg
                except ValueError:
                    return False, f"Invalid port number: {port_str}"
        return True, ""

    # Handle port ranges
    if '-' in port_range:
        try:
            start, end = map(int, port_range.split('-'))
            if start > end:
                return False, "Port range start must be less than end"

            is_valid, msg = validate_port(start)
            if not is_valid:
                return False, msg

            is_valid, msg = validate_port(end)
            return (True, "") if is_valid else (False, msg)
        except ValueError:
            return False, "Invalid port range format"

    # Single port
    try:
        port = int(port_range)
        return validate_port(port)
    except ValueError:
        return False, "Invalid port specification"


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic URL validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    return (True, "") if url_pattern.match(url) else (False, "Invalid URL format")


def sanitize_input(value: str) -> str:
    """
    Sanitize user input to prevent command injection.
    
    Args:
        value: Input value to sanitize
    
    Returns:
        Sanitized value
    """
    # Remove shell metacharacters and non-printable control characters
    dangerous_chars = [';', '|', '&', '$', '`', '(', ')', '<', '>', '\n', '\r', "'", '"', '\\', '!', '{', '}', '\t', '\x00']
    for char in dangerous_chars:
        value = value.replace(char, '')
    
    return value.strip()


def is_safe_path(path: str, base_dir: str) -> bool:
    """
    Check if a path is safe (no directory traversal).
    
    Args:
        path: Path to check
        base_dir: Base directory to restrict to
    
    Returns:
        True if path is safe
    """
    import os
    try:
        real_base = os.path.realpath(base_dir)
        real_path = os.path.realpath(os.path.join(base_dir, path))
        return real_path.startswith(real_base)
    except Exception:
        return False


def match_pattern(value: str, pattern: str) -> bool:
    """
    Match value against wildcard pattern.
    
    Args:
        value: Value to match
        pattern: Pattern with wildcards (* and ?)
    
    Returns:
        True if value matches pattern
    """
    return fnmatch(value, pattern)


# ---------------------------------------------------------------------------
# Task-start payload size/length validation
# ---------------------------------------------------------------------------

def validate_task_start_payload(raw_body: bytes, inputs: Dict[str, Any]) -> Tuple[bool, int, str]:
    """
    Enforce size and field-length limits on POST /task/start payloads.

    Checks are run in order:
      1. Total body size  → HTTP 413
      2. inputs dict type → HTTP 400
      3. Per-field string length and array length → HTTP 400

    Error messages never echo back input values to avoid leaking sensitive
    or oversized data into logs/responses.

    Args:
        raw_body: Raw request bytes (for total-size check).
        inputs:   The parsed ``inputs`` dict from the request body.

    Returns:
        (ok, status_code, error_message)
        ok is True and status_code is 0 when all checks pass.
    """
    # 1. Total body size
    if len(raw_body) > settings.task_start_max_body_bytes:
        return (
            False,
            413,
            f"Request body exceeds the maximum allowed size of "
            f"{settings.task_start_max_body_bytes} bytes.",
        )

    # 2. inputs must be a dict
    if not isinstance(inputs, dict):
        return False, 400, "'inputs' must be a JSON object."

    # 3. Per-field checks
    for key, value in inputs.items():
        ok, status, msg = _check_field(key, value)
        if not ok:
            return ok, status, msg

    return True, 0, ""


def _check_field(key: str, value: Any) -> Tuple[bool, int, str]:
    """Check a single input field value (string or list)."""
    if isinstance(value, str):
        if len(value) > settings.task_start_max_field_length:
            # Do NOT include the value itself — it may be huge or sensitive.
            return (
                False,
                400,
                f"Input field '{key}' exceeds the maximum allowed length of "
                f"{settings.task_start_max_field_length} characters.",
            )

    elif isinstance(value, list):
        if len(value) > settings.task_start_max_array_length:
            return (
                False,
                400,
                f"Input field '{key}' contains too many items "
                f"(max {settings.task_start_max_array_length}).",
            )
        for idx, item in enumerate(value):
            if isinstance(item, str) and len(item) > settings.task_start_max_field_length:
                return (
                    False,
                    400,
                    f"Item at index {idx} in input field '{key}' exceeds the "
                    f"maximum allowed length of "
                    f"{settings.task_start_max_field_length} characters.",
                )

    return True, 0, ""