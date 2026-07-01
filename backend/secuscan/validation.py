"""
Input validation and security checks
"""

import re
import ipaddress
import socket
import time
from urllib.parse import urlparse
from typing import Any, Dict, Tuple, Optional
from fnmatch import fnmatch

import logging

from .config import settings

logger = logging.getLogger(__name__)


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


def _net_within_allowed_networks(net: ipaddress._BaseNetwork) -> bool:
    """Return True if net is permitted by settings.allowed_networks (best-effort, conservative)."""
    patterns = [str(p).strip() for p in (settings.allowed_networks or []) if str(p).strip()]
    if not patterns:
        return True

    def wildcard_to_net(pattern: str) -> ipaddress.IPv4Network | None:
        # Convert simple trailing-octet wildcards like "10.*.*.*" → 10.0.0.0/8.
        parts = pattern.split(".")
        if len(parts) != 4:
            return None
        fixed = []
        wildcard_started = False
        for part in parts:
            if part == "*":
                wildcard_started = True
                fixed.append(0)
                continue
            if wildcard_started:
                return None
            if not part.isdigit():
                return None
            value = int(part)
            if value < 0 or value > 255:
                return None
            fixed.append(value)
        wildcard_octets = sum(1 for p in parts if p == "*")
        if wildcard_octets == 0:
            return None
        prefix = (4 - wildcard_octets) * 8
        return ipaddress.IPv4Network(f"{'.'.join(map(str, fixed))}/{prefix}", strict=False)

    # Single-IP networks can be checked against wildcards and CIDRs.
    if net.num_addresses == 1:
        ip_str = str(net.network_address)
        for pattern in patterns:
            try:
                allowed_net = ipaddress.ip_network(pattern, strict=False)
                if net.version != allowed_net.version:
                    continue
                if net.subnet_of(allowed_net) or net.overlaps(allowed_net):
                    return True
            except ValueError:
                converted = wildcard_to_net(pattern)
                if converted and net.version == converted.version and net.subnet_of(converted):
                    return True
                if fnmatch(ip_str, pattern):
                    return True
        return False

    # Multi-address networks: only allow explicit CIDR allowlist entries that fully contain the target.
    for pattern in patterns:
        try:
            allowed_net = ipaddress.ip_network(pattern, strict=False)
        except ValueError:
            allowed_net = wildcard_to_net(pattern)
            if not allowed_net:
                continue
        if net.version == allowed_net.version and net.subnet_of(allowed_net):
            return True

    return False


def _parse_url_hostname(target: str) -> str | None:
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"}:
        return None
    return parsed.hostname


def _resolve_host_ips(hostname: str) -> list[ipaddress._BaseAddress]:
    """Resolve hostname to a list of IP addresses (A/AAAA).

    Note: This function is synchronous and may block on DNS resolution. Callers
    in async request paths should run it in a thread and enforce timeouts.
    Results are cached for a short TTL to reduce repeated resolutions.
    """
    now = time.time()
    cached = _DNS_CACHE.get(hostname)
    if cached and cached[0] > now:
        return list(cached[1])
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except OSError:
        _DNS_CACHE[hostname] = (now + max(1, int(settings.dns_cache_ttl_seconds)), [])
        return []
    ips: list[ipaddress._BaseAddress] = []
    for family, _socktype, _proto, _canonname, sockaddr in infos:
        try:
            if family == socket.AF_INET:
                ips.append(ipaddress.ip_address(sockaddr[0]))
            elif family == socket.AF_INET6:
                ips.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue
    # Deduplicate while preserving order.
    seen = set()
    unique = []
    for ip in ips:
        if ip in seen:
            continue
        seen.add(ip)
        unique.append(ip)
    _DNS_CACHE[hostname] = (now + max(1, int(settings.dns_cache_ttl_seconds)), unique)
    return list(unique)


def _resolve_host_ips_uncached(hostname: str) -> list[ipaddress._BaseAddress]:
    """Force a fresh DNS resolution (bypasses TTL cache)."""
    _DNS_CACHE.pop(hostname, None)
    return _resolve_host_ips(hostname)


def _validate_resolved_ips_safe_mode(resolved_ips: list[ipaddress._BaseAddress]) -> Tuple[bool, str]:
    if not resolved_ips:
        return False, "Hostname did not resolve to any IPs in safe mode (SecuScan Guardrail)"

    for ip in resolved_ips:
        ip_net = ipaddress.ip_network(ip, strict=False)
        if any(ip_net.overlaps(blocked) for blocked in BLOCKED_NETWORKS):
            return False, "Target overlaps with blocked network range"
        if ip.is_loopback and not settings.allow_loopback_scans:
            return False, "Loopback scans are disabled in global settings"

        is_private = any(
            (ip_net.version == allowed.version and (ip_net.subnet_of(allowed) or ip_net.overlaps(allowed)))
            for allowed in ALLOWED_PRIVATE
        )
        if not is_private:
            return False, "Public IPs/networks not allowed in safe mode (SecuScan Guardrail)"
        if not _net_within_allowed_networks(ip_net):
            return False, "Target not within allowed networks in safe mode (SecuScan Guardrail)"

    return True, ""


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

            if not _net_within_allowed_networks(net):
                return False, "Target not within allowed networks in safe mode (SecuScan Guardrail)"

        return True, ""

    except ValueError:
        # Not an IP address or network, treat as hostname/URL
        pass

    # Handle URLs
    hostname_to_validate = target
    parsed_host = _parse_url_hostname(target)
    if parsed_host is not None:
        hostname_to_validate = parsed_host

    # If host is an IP literal (including URL host), validate it via the same IP/CIDR path.
    try:
        net = ipaddress.ip_network(hostname_to_validate, strict=False)
        return validate_target(str(net), safe_mode=safe_mode)
    except ValueError:
        pass

    # Validate hostname format (RFC 1123)
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', hostname_to_validate):
        return False, "Invalid hostname format"

    # Check blocked TLDs in safe mode
    if safe_mode:
        for tld in BLOCKED_TLDS:
            if hostname_to_validate.lower().endswith(tld):
                return False, f"Domains ending in {tld} are blocked in safe mode"

        # Safe mode: resolve hostname and ensure ALL resolved IPs are within private + allowed networks.
        # Also protect against rebinding/round-robin by optionally doing a second fresh resolution and validating the union.
        resolved_ips = _resolve_host_ips(hostname_to_validate)
        ok, msg = _validate_resolved_ips_safe_mode(resolved_ips)
        if not ok:
            return ok, msg

        if settings.dns_rebind_check:
            resolved_ips2 = _resolve_host_ips_uncached(hostname_to_validate)
            union = []
            seen = set()
            for ip in list(resolved_ips) + list(resolved_ips2):
                if ip in seen:
                    continue
                seen.add(ip)
                union.append(ip)
            ok2, msg2 = _validate_resolved_ips_safe_mode(union)
            if not ok2:
                return ok2, msg2

    return True, ""


# Simple TTL cache: hostname -> (expires_at_epoch, [ips])
_DNS_CACHE: dict[str, tuple[float, list[ipaddress._BaseAddress]]] = {}


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
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    if not url_pattern.match(url):
        return False, "Invalid URL format"

    port_match = re.search(r':(\d+)(?:/|\?|$)', url.split('://', 1)[1])
    if port_match:
        port = int(port_match.group(1))
        if port < 1 or port > 65535:
            return False, "Invalid URL format"

    return True, ""


def validate_webhook_target(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate webhook URL against SSRF attacks by resolving DNS and
    checking resolved IPs against blocked/private networks.

    Uses the configured SECUSCAN_NOTIFICATION_BLOCKED_IP_RANGES to determine
    which IP ranges to reject. This runs independently of enforce_network_policy
    so webhook SSRF protection is always active.

    Args:
        url: Webhook URL to validate

    Returns:
        Tuple of (is_safe, error_message)
    """
    hostname = urlparse(url).hostname
    if not hostname:
        return False, "Webhook URL has no hostname"

    try:
        addrs = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False, "Webhook URL hostname could not be resolved"

    for addr in addrs:
        try:
            ip = ipaddress.ip_address(addr[4][0])
        except ValueError:
            continue
        for blocked_cidr in settings.notification_blocked_ip_ranges:
            try:
                if ip in ipaddress.ip_network(blocked_cidr, strict=False):
                    return False, f"Webhook URL resolves to blocked address ({ip}) in range {blocked_cidr}"
            except ValueError:
                continue
    return True, None


def sanitize_input(value: str) -> str:
    """
    Sanitize user input to prevent command injection.
    
    Args:
        value: Input value to sanitize
    
    Returns:
        Sanitized value
    """
    # Convert backslashes to forward slashes to preserve path separators on Windows.
    value = value.replace('\\', '/')

    # Remove shell metacharacters and non-printable control characters.
    dangerous_chars = [';', '|', '&', '$', '`', '(', ')', '<', '>', '\n', '\r', "'", '"', '\\', '!', '{', '}', '\t', '\x00']
    for char in dangerous_chars:
        value = value.replace(char, '')

    # User-controlled placeholders are passed as argv values, not through a
    # shell, but leading dashes can still be interpreted as tool options.
    value = value.lstrip("-")

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
    except Exception as exc:
        logger.debug("path safety check failed (returning False): %s", exc)
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

def validate_task_start_payload(
    raw_body: bytes,
    inputs: Dict[str, Any],
    execution_context: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, int, str]:
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

    if execution_context is not None:
        if not isinstance(execution_context, dict):
            return False, 400, "'execution_context' must be a JSON object."
        for key, value in execution_context.items():
            ok, status, msg = _check_field(f"execution_context.{key}", value)
            if not ok:
                return ok, status, msg

    return True, 0, ""


def validate_preset_name(
    plugin_id: str,
    preset: Optional[str],
    presets: Optional[Dict[str, Any]],
) -> Tuple[bool, str]:
    """Validate that an optional preset name exists for the selected plugin."""
    if preset in (None, ""):
        return True, ""

    available_presets = presets or {}
    if preset not in available_presets:
        return False, f"Unknown preset '{preset}' for plugin '{plugin_id}'"

    return True, ""


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
            ok, status, msg = _check_field(f"{key}[{idx}]", item)
            if not ok:
                return ok, status, msg

    elif isinstance(value, dict):
        for child_key, child_value in value.items():
            ok, status, msg = _check_field(f"{key}.{child_key}", child_value)
            if not ok:
                return ok, status, msg

    return True, 0, ""

def is_filesystem_target(target: str) -> bool:
    """Best-effort detection for path-based targets that should bypass host validation.

    Returns True only for genuine local filesystem paths:
      - Unix absolute paths:   /home/user/repo
      - Unix relative paths:   ./src, ../lib
      - Home-relative paths:   ~/projects
      - Windows paths:         C:\\Users\\repo, D:/work

    CIDR notation (e.g. 8.8.8.8/32), bare hostnames, URLs, and
    domain paths all return False and are subject to validate_target().
    """
    # Unix absolute, relative, and home-relative paths
    if target.startswith(("/", "./", "../", "~/")):
        return True
    # Windows paths: C:\\ or C:/
    if re.match(r"^[A-Za-z]:[\\/]", target):
        return True
    return False

def resolve_and_validate_target(url: str) -> Tuple[bool, str]:
    """Resolve a webhook URL and validate it against SSRF protections.

    Performs DNS resolution, IP range validation, and port checks
    to prevent Server-Side Request Forgery attacks.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL"

    if parsed.scheme not in ("http", "https"):
        return False, f"Scheme '{parsed.scheme}' not allowed for webhooks"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must have a hostname"

    port = parsed.port
    if port is not None and port not in settings.notification_allowed_ports:
        return False, f"Port {port} not in allowed ports: {settings.notification_allowed_ports}"

    # Reject raw IP addresses in webhook URLs
    try:
        ipaddress.ip_address(hostname)
        return False, "Raw IP addresses are not allowed in webhook URLs; use a hostname"
    except ValueError:
        pass

    # Resolve hostname to IPs
    try:
        resolved = socket.getaddrinfo(hostname, port or 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return False, f"Could not resolve hostname: {hostname}"

    for family, _socktype, _proto, _canonname, sockaddr in resolved:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue

        # Check against blocked ranges
        for blocked_cidr in settings.notification_blocked_ip_ranges:
            try:
                blocked_net = ipaddress.ip_network(blocked_cidr, strict=False)
                if ip in blocked_net:
                    return False, f"Resolved IP {ip} falls in blocked range {blocked_cidr}"
            except ValueError:
                continue

        # Check allowed ranges if configured
        if settings.notification_allowed_ip_ranges:
            in_allowed = False
            for allowed_cidr in settings.notification_allowed_ip_ranges:
                try:
                    allowed_net = ipaddress.ip_network(allowed_cidr, strict=False)
                    if ip in allowed_net:
                        in_allowed = True
                        break
                except ValueError:
                    continue
            if not in_allowed:
                return False, f"Resolved IP {ip} not in allowed ranges"

    return True, ""


def validate_command_network_egress(command: list[str], safe_mode: bool, plugin_id: str, task_id: str) -> Tuple[bool, str]:
    """
    Inspect all command arguments. If any argument represents an outbound network
    destination (IP, hostname, URL), validate it against both Safe Mode and Network Policy.
    """
    from .network_policy import get_policy_engine

    for arg in command:
        arg_str = str(arg).strip()
        if not arg_str:
            continue
        if arg_str.startswith("-"):
            continue  # Ignore flags
        if is_filesystem_target(arg_str):
            continue  # Ignore local paths

        # Check if it looks like a URL
        is_url = False
        hostname = None
        if "://" in arg_str:
            try:
                parsed = urlparse(arg_str)
                if parsed.scheme in ("http", "https", "ws", "wss"):
                    is_url = True
                    hostname = parsed.hostname
            except Exception:
                pass

        # If it's a URL, validate the hostname. If not, check if it could be a hostname or IP.
        candidate = hostname if is_url else arg_str
        if not candidate:
            continue

        # Clean port suffix if present (e.g. "example.com:80" or "10.0.0.1:8080")
        if ":" in candidate and not candidate.startswith("["):
            parts = candidate.rsplit(":", 1)
            if parts[1].isdigit():
                candidate = parts[0]

        is_ip = False
        try:
            # Try to parse as IP/CIDR (handles single IP and subnet validation)
            ipaddress.ip_network(candidate, strict=False)
            is_ip = True
        except ValueError:
            pass

        is_host = False
        if not is_ip:
            # Basic hostname check (with dots and valid characters, or 'localhost')
            if candidate.lower() == "localhost" or re.match(
                r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+$',
                candidate
            ):
                is_host = True

        if is_ip or is_host:
            # Validate against safe mode
            is_valid, err = validate_target(candidate, safe_mode=safe_mode)
            if not is_valid:
                return False, f"Command argument '{arg_str}' violates safe mode: {err}"

            # Validate against network policy
            if settings.enforce_network_policy:
                engine = get_policy_engine()
                allowed, reason, _ = engine.check_access(
                    dest_ip=candidate,
                    plugin_id=plugin_id,
                    task_id=task_id,
                )
                if not allowed:
                    if settings.network_policy_failure_mode == "log_only":
                        import logging
                        logging.getLogger(__name__).warning(
                            f"[Log Only] Command argument '{arg_str}' network policy violation allowed: {reason}"
                        )
                    else:
                        return False, f"Command argument '{arg_str}' violates network policy: {reason}"

    return True, ""
