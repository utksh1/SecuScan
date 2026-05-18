"""
Input validation and security checks
"""

import re
import ipaddress
from typing import Tuple, Dict, Any
from fnmatch import fnmatch

from .config import settings


# Blocked network ranges
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),
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


def extract_target_from_inputs(inputs: Dict[str, Any]) -> str:
    """
    Best-effort target extraction across plugin shapes.
    Centralized shared helper for routes/executor/plugins.

    Args:
        inputs: User-provided plugin inputs

    Returns:
        Extracted target string
    """
    return (
        inputs.get("target")
        or inputs.get("url")
        or inputs.get("host")
        or inputs.get("domain")
        or ""
    )


def sanitize_input(value: str) -> str:
    """
    Sanitize user input to reduce command injection risk.

    Args:
        value: Input value to sanitize

    Returns:
        Sanitized value
    """
    dangerous_chars = [';', '|', '&', '$', '`', '(', ')', '<', '>', '\n', '\r']
    
    for char in dangerous_chars:
        value = value.replace(char, '')

    return value.strip()


def sanitize_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize string-based user inputs.

    Args:
        inputs: Raw user inputs

    Returns:
        Sanitized input dictionary
    """
    sanitized: Dict[str, Any] = {}

    for key, value in inputs.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_input(value)

        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_input(v) if isinstance(v, str) else v
                for v in value
            ]

        elif isinstance(value, dict):
            sanitized[key] = sanitize_inputs(value)

        else:
            sanitized[key] = value

    return sanitized


def validate_task_inputs(
    inputs: Dict[str, Any],
    safe_mode: bool = True
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Centralized validation boundary for task inputs.

    Responsibilities:
    - sanitize inputs
    - extract target consistently
    - validate targets
    - normalize payload structure

    Args:
        inputs: Raw task inputs
        safe_mode: Whether safe mode restrictions apply

    Returns:
        Tuple:
        (
            is_valid,
            error_message,
            sanitized_inputs
        )
    """
    sanitized_inputs = sanitize_inputs(inputs)

    target = extract_target_from_inputs(sanitized_inputs)

    if target:
        is_valid, error_msg = validate_target(
            str(target),
            safe_mode=safe_mode
        )

        if not is_valid:
            return False, error_msg, sanitized_inputs

    return True, "", sanitized_inputs


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

    # Try parsing as IP network
    try:
        net = ipaddress.ip_network(target, strict=False)

        # Check blocked networks
        if any(net.overlaps(blocked) for blocked in BLOCKED_NETWORKS):
            return False, "Target overlaps with blocked network range"

        # Loopback restrictions
        if net.is_loopback and not settings.allow_loopback_scans:
            return False, "Loopback scans are disabled in global settings"

        # Safe mode restrictions
        if safe_mode:
            is_private = any(
                (
                    net.version == allowed.version
                    and (
                        net.subnet_of(allowed)
                        or net.overlaps(allowed)
                    )
                )
                for allowed in ALLOWED_PRIVATE
            )

            if not is_private:
                return False, (
                    "Public IPs/networks not allowed "
                    "in safe mode (SecuScan Guardrail)"
                )

        return True, ""

    except ValueError:
        pass

    # Handle URLs
    hostname_to_validate = target

    if target.startswith(("http://", "https://")):
        hostname_to_validate = (
            target.split("://", 1)[1]
            .split("/", 1)[0]
            .split(":", 1)[0]
        )

    # Hostname validation
    hostname_pattern = (
        r'^[a-zA-Z0-9]'
        r'([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
        r'(\.[a-zA-Z0-9]'
        r'([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    )

    if not re.match(hostname_pattern, hostname_to_validate):
        return False, "Invalid hostname format"

    # Block restricted TLDs
    if safe_mode:
        for tld in BLOCKED_TLDS:
            if hostname_to_validate.lower().endswith(tld):
                return False, (
                    f"Domains ending in {tld} "
                    "are blocked in safe mode"
                )

    return True, ""


def validate_port(port: int) -> Tuple[bool, str]:
    """
    Validate port number.
    """
    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535"

    return True, ""


def validate_port_range(port_range: str) -> Tuple[bool, str]:
    """
    Validate port range specification.
    """
    # Comma-separated ports
    if ',' in port_range:
        for port_str in port_range.split(','):
            try:
                port = int(port_str.strip())

                is_valid, msg = validate_port(port)

                if not is_valid:
                    return False, msg

            except ValueError:
                return False, f"Invalid port number: {port_str}"

        return True, ""

    # Port ranges
    if '-' in port_range:
        try:
            start, end = map(int, port_range.split('-'))

            if start > end:
                return False, (
                    "Port range start must be less than end"
                )

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
    """
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9]'
        r'(?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
        r'[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )

    return (
        (True, "")
        if url_pattern.match(url)
        else (False, "Invalid URL format")
    )


def is_safe_path(path: str, base_dir: str) -> bool:
    """
    Check if a path is safe (no directory traversal).
    """
    import os

    try:
        real_base = os.path.realpath(base_dir)
        real_path = os.path.realpath(
            os.path.join(base_dir, path)
        )

        return real_path.startswith(real_base)

    except Exception:
        return False


def match_pattern(value: str, pattern: str) -> bool:
    """
    Match value against wildcard pattern.
    """
    return fnmatch(value, pattern)