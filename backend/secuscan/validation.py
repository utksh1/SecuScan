"""
Input validation and security checks
"""

import re
import ipaddress
from typing import Any, Dict, Tuple
from fnmatch import fnmatch

from .config import settings


# Blocked network ranges
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),       # Broadcast
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("224.0.0.0/4"),     # Multicast
]

# Allowed private IP ranges
ALLOWED_PRIVATE = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]

# Blocked TLDs in safe mode
BLOCKED_TLDS = [".mil", ".gov"]


def validate_target(target: str, safe_mode: bool = True) -> Tuple[bool, str]:
    """
    Validate scan target address (IP, Hostname, URL, or CIDR).
    
    Args:
        target: IP address, hostname, or network range to validate
        safe_mode: Whether to enforce safe mode restrictions
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    target = target.strip()
    if not target:
        return False, "Target cannot be empty"

    # Try parsing as IP network (handles single IP and CIDR)
    try:
        net = ipaddress.ip_network(target, strict=False)
        
        # Check blocked networks (Broadcast, Link-local, Multicast)
        if any(net.overlaps(blocked) for blocked in BLOCKED_NETWORKS):
            return False, "Target overlaps with blocked network range"

        # Check for loopback even in non-safe mode if desired (usually allowed for local debugging)
        if net.is_loopback and not settings.allow_loopback_scans:
            return False, "Loopback scans are disabled in global settings"

        # Safe mode: only allow private IPs
        if safe_mode:
            is_private = any(
                (net.version == allowed.version and (net.subnet_of(allowed) or net.overlaps(allowed)))
                for allowed in ALLOWED_PRIVATE
            )
            if not is_private:
                return False, "Public IPs/networks not allowed in safe mode (SecuScan Guardrail)"

        return True, ""

    except ValueError:
        # Not an IP address or network, treat as hostname/URL
        pass

    # Handle URLs
    hostname_to_validate = target
    if target.startswith(("http://", "https://")):
        # Extract host:port or host (handle IPv6 literals in brackets)
        host_part = target.split("://", 1)[1].split("/", 1)[0]
        if host_part.startswith("["):
            # IPv6 literal like [::1]:8080 or [::1] for ipv6
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

    return True, ""


def validate_port(port: int) -> Tuple[bool, str]:
    """
    Validate port number.
    
    Args:
        port: Port number to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535"
    
    return True, ""


def validate_port_range(port_range: str) -> Tuple[bool, str]:
    """
    Validate port range specification.
    
    Args:
        port_range: Port range string (e.g., "80,443" or "1-1000")
    
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
    # Remove shell metacharacters
    dangerous_chars = [';', '|', '&', '$', '`', '(', ')', '<', '>', '\n', '\r', "'", '"', '\\', '!', '{', '}']
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