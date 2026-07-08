"""
Network egress policy enforcement for scanners.

Implements deny-by-default network access control with configurable
allowlist/denylist policies. Supports both IPv4 and IPv6.
"""

import ipaddress
import logging
import asyncio
import socket
from typing import List, Tuple, Optional, Dict, Any
from urllib.parse import urlparse
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

class PolicyAction(Enum):
    """Network policy decision outcome"""
    ALLOW = "allow"
    DENY = "deny"

@dataclass
class NetworkPolicy:
    """Single network access policy rule"""
    cidr: str                      # Network in CIDR notation
    action: PolicyAction          # Allow or deny
    reason: str                   # Why this rule exists
    created_at: datetime          # When rule was added
    expires_at: Optional[datetime] = None  # Optional expiration

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "cidr": self.cidr,
            "action": self.action.value,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

@dataclass
class AuditLogEntry:
    """Network access audit trail entry"""
    timestamp: datetime
    plugin_id: str
    task_id: str
    action: PolicyAction
    dest_ip: str
    dest_port: int
    dest_hostname: Optional[str]
    policy_matched: str           # CIDR that caused decision
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON logging"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "plugin_id": self.plugin_id,
            "task_id": self.task_id,
            "action": self.action.value,
            "dest_ip": self.dest_ip,
            "dest_port": self.dest_port,
            "dest_hostname": self.dest_hostname,
            "policy_matched": self.policy_matched,
            "reason": self.reason,
        }

class NetworkPolicyEngine:
    """
    Enforce network access policies for scanners.

    Logic:
      1. Check explicit denylist (highest priority, fails fast)
      2. Check explicit allowlist (allows if matched)
      3. Default deny (no match = blocked)
    """

    def __init__(self, audit_log_path: str = "/var/log/secuscan/network.audit.log"):
        self.allowlist: List[Tuple[ipaddress.ip_network, NetworkPolicy]] = []
        self.denylist: List[Tuple[ipaddress.ip_network, NetworkPolicy]] = []
        self.audit_log_path = audit_log_path
        self.audit_entries: List[AuditLogEntry] = []

        # Create audit log file
        self._init_audit_log()

    def _init_audit_log(self):
        """Initialize audit log file with header"""
        try:
            # Ensure the directory exists
            Path(self.audit_log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_log_path, 'a') as f:
                if f.tell() == 0:  # Empty file
                    f.write("# SecuScan Network Audit Log\n")
                    f.write(f"# Started: {datetime.now().isoformat()}\n")
        except IOError as e:
            logger.error(f"Failed to initialize audit log: {e}")

    def add_allow_rule(
        self,
        cidr: str,
        reason: str = "Operator configured",
        expires_at: Optional[datetime] = None
    ) -> None:
        """
        Add a network to the allowlist.

        Args:
            cidr: Network in CIDR notation (e.g., "10.0.0.0/8")
            reason: Human-readable reason for this rule
            expires_at: Optional expiration timestamp
        """
        try:
            net = ipaddress.ip_network(cidr, strict=False)
            policy = NetworkPolicy(
                cidr=cidr,
                action=PolicyAction.ALLOW,
                reason=reason,
                created_at=datetime.now(),
                expires_at=expires_at,
            )
            self.allowlist.append((net, policy))
            logger.info(f"Added allow rule for {cidr}: {reason}")
        except ValueError as e:
            logger.error(f"Invalid CIDR in allowlist: {cidr}: {e}")
            raise

    def add_deny_rule(
        self,
        cidr: str,
        reason: str = "System blocked",
        expires_at: Optional[datetime] = None
    ) -> None:
        """
        Add a network to the denylist.

        Args:
            cidr: Network in CIDR notation
            reason: Human-readable reason for this rule
            expires_at: Optional expiration timestamp
        """
        try:
            net = ipaddress.ip_network(cidr, strict=False)
            policy = NetworkPolicy(
                cidr=cidr,
                action=PolicyAction.DENY,
                reason=reason,
                created_at=datetime.now(),
                expires_at=expires_at,
            )
            self.denylist.append((net, policy))
            logger.info(f"Added deny rule for {cidr}: {reason}")
        except ValueError as e:
            logger.error(f"Invalid CIDR in denylist: {cidr}: {e}")
            raise

    def check_access(
        self,
        dest_ip: str,
        dest_port: int = 0,
        plugin_id: str = "unknown",
        task_id: str = "unknown",
        dest_hostname: Optional[str] = None,
    ) -> Tuple[bool, str, NetworkPolicy]:
        """
        Check if outbound connection is allowed.

        Args:
            dest_ip: Destination IP address
            dest_port: Destination port (informational)
            plugin_id: Plugin making the connection
            task_id: Task ID for audit context
            dest_hostname: Optional resolved hostname

        Returns:
            Tuple of (allowed: bool, decision_reason: str, matched_policy: NetworkPolicy)
        """
        # Clean dest_ip if it is a full URL, has a port, or has brackets
        original_dest_ip = dest_ip
        target_host = dest_ip.strip()
        if "://" in target_host:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(target_host)
                if parsed.scheme in {"http", "https", "ws", "wss"}:
                    if parsed.hostname:
                        target_host = parsed.hostname
            except Exception as exc:
                logger.debug(
                    "Failed to parse URL while normalizing network policy target '%s': %s",
                    original_dest_ip,
                    exc,
                )

        if ":" in target_host:
            if target_host.startswith("["):
                if "]" in target_host:
                    parts = target_host.rsplit("]", 1)
                    host_part = parts[0] + "]"
                    port_part = parts[1]
                    if port_part.startswith(":") and port_part[1:].isdigit():
                        target_host = host_part
            elif target_host.count(":") == 1:
                parts = target_host.rsplit(":", 1)
                if parts[1].isdigit():
                    target_host = parts[0]
        if target_host.startswith("[") and target_host.endswith("]"):
            target_host = target_host[1:-1]

        try:
            ip = ipaddress.ip_address(target_host)
            dest_ip = str(ip)
        except ValueError:
            # Try resolving hostname to IP if target_host is a domain name
            try:
                resolved = socket.gethostbyname(target_host)
                ip = ipaddress.ip_address(resolved)
                if not dest_hostname:
                    dest_hostname = target_host
                dest_ip = resolved
            except Exception:
                reason = f"Invalid IP address format: {original_dest_ip}"
                entry = AuditLogEntry(
                    timestamp=datetime.now(),
                    plugin_id=plugin_id,
                    task_id=task_id,
                    action=PolicyAction.DENY,
                    dest_ip=original_dest_ip,
                    dest_port=dest_port,
                    dest_hostname=dest_hostname,
                    policy_matched="invalid_ip",
                    reason=reason,
                )
                self._log_audit_entry(entry)
                return False, reason, None

        # ═ Step 1: Check denylist (highest priority) ═
        for net, policy in self.denylist:
            if self._is_expired(policy):
                continue
            if ip in net:
                reason = f"Blocked by denylist rule: {policy.reason} (matched: {policy.cidr})"
                entry = AuditLogEntry(
                    timestamp=datetime.now(),
                    plugin_id=plugin_id,
                    task_id=task_id,
                    action=PolicyAction.DENY,
                    dest_ip=dest_ip,
                    dest_port=dest_port,
                    dest_hostname=dest_hostname,
                    policy_matched=policy.cidr,
                    reason=reason,
                )
                self._log_audit_entry(entry)
                return False, reason, policy

        # ═ Step 2: Check allowlist ═
        for net, policy in self.allowlist:
            if self._is_expired(policy):
                continue
            if ip in net:
                reason = f"Allowed by allowlist rule: {policy.reason} (matched: {policy.cidr})"
                entry = AuditLogEntry(
                    timestamp=datetime.now(),
                    plugin_id=plugin_id,
                    task_id=task_id,
                    action=PolicyAction.ALLOW,
                    dest_ip=dest_ip,
                    dest_port=dest_port,
                    dest_hostname=dest_hostname,
                    policy_matched=policy.cidr,
                    reason=reason,
                )
                self._log_audit_entry(entry)
                return True, reason, policy

        # ═ Step 3: Default deny ═
        reason = "Denied by default (no matching allow rule)"
        deny_policy = NetworkPolicy(
            cidr="0.0.0.0/0",
            action=PolicyAction.DENY,
            reason="Default deny policy",
            created_at=datetime.now(),
        )
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            plugin_id=plugin_id,
            task_id=task_id,
            action=PolicyAction.DENY,
            dest_ip=dest_ip,
            dest_port=dest_port,
            dest_hostname=dest_hostname,
            policy_matched="default",
            reason=reason,
        )
        self._log_audit_entry(entry)
        return False, reason, deny_policy

    def resolve_and_pin(
        self,
        target: str,
        plugin_id: str = "unknown",
        task_id: str = "unknown",
    ) -> Tuple[Optional[str], bool, str]:
        """Resolve target hostname once and validate against network policy.

        Pins the resolved IP so the scanner subprocess cannot be victimized
        by a DNS rebinding attack (where DNS switches to a malicious IP
        between policy check and scan execution). Passes plugin/task context
        through to the audit trail in check_access.

        Args:
            target: Hostname or IP address to resolve.
            plugin_id: Plugin making the request (for audit trail).
            task_id: Task ID (for audit trail).

        Returns:
            Tuple of (pinned_ip, is_allowed, reason).
            pinned_ip is None if the hostname is unresolvable.
        """
        try:
            ip = ipaddress.ip_address(target)
            pinned = str(ip)
            allowed, reason, _ = self.check_access(
                dest_ip=pinned, dest_hostname=target,
                plugin_id=plugin_id, task_id=task_id,
            )
            return (pinned, allowed, reason)
        except ValueError:
            pass

        try:
            resolved = socket.gethostbyname(target)
            ipaddress.ip_address(resolved)
            allowed, reason, _ = self.check_access(
                dest_ip=resolved, dest_hostname=target,
                plugin_id=plugin_id, task_id=task_id,
            )
            return (resolved, allowed, reason)
        except socket.gaierror:
            return (None, False, f"Unresolvable hostname: {target}")

    def _is_expired(self, policy: NetworkPolicy) -> bool:
        """Check if a policy has expired"""
        if policy.expires_at is None:
            return False
        return datetime.now() > policy.expires_at

    def _log_audit_entry(self, entry: AuditLogEntry) -> None:
        """Log audit entry to file and memory"""
        self.audit_entries.append(entry)

        try:
            with open(self.audit_log_path, 'a') as f:
                import json
                f.write(json.dumps(entry.to_dict()) + "\n")
        except IOError as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_audit_entries(
        self,
        plugin_id: Optional[str] = None,
        action: Optional[PolicyAction] = None,
        limit: int = 1000
    ) -> List[AuditLogEntry]:
        """
        Retrieve audit log entries with optional filtering.

        Args:
            plugin_id: Filter by plugin (optional)
            action: Filter by action (ALLOW or DENY)
            limit: Maximum number of entries to return

        Returns:
            List of matching audit entries
        """
        entries = self.audit_entries

        if plugin_id:
            entries = [e for e in entries if e.plugin_id == plugin_id]

        if action:
            entries = [e for e in entries if e.action == action]

        return entries[-limit:]  # Return most recent N

    def validate_egress_target(self, host: str, port: int = 443) -> Tuple[bool, str]:
        """Validate an outbound webhook/egress destination against network policy.

        Args:
            host: Hostname to validate
            port: Destination port

        Returns:
            Tuple of (allowed, reason)
        """
        target_host = host
        if "://" in target_host:
            try:
                parsed = urlparse(target_host)
                if parsed.hostname:
                    target_host = parsed.hostname
            except Exception as exc:
                logger.debug(
                    "Failed to parse egress target '%s' as URL: %s",
                    host,
                    exc,
                )

        try:
            ip = ipaddress.ip_address(target_host)
        except ValueError:
            try:
                resolved = socket.gethostbyname(target_host)
                ip = ipaddress.ip_address(resolved)
            except Exception:
                return False, f"Could not resolve host: {target_host}"

        for net, policy in self.denylist:
            if not self._is_expired(policy) and ip in net:
                return False, f"Destination blocked by policy: {policy.reason}"

        for net, policy in self.allowlist:
            if not self._is_expired(policy) and ip in net:
                return True, ""

        return False, "Destination denied by default policy"

    def export_audit_log(self, format: str = "json") -> str:
        """
        Export audit log in specified format.

        Args:
            format: "json" or "csv"

        Returns:
            Formatted audit log string
        """
        if format == "csv":
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                'timestamp', 'plugin_id', 'task_id', 'action',
                'dest_ip', 'dest_port', 'dest_hostname', 'policy_matched', 'reason'
            ])
            writer.writeheader()
            for entry in self.audit_entries:
                writer.writerow(entry.to_dict())
            return output.getvalue()
        else:  # JSON
            import json
            return json.dumps([e.to_dict() for e in self.audit_entries], indent=2)

# Global policy engine instance
_policy_engine: Optional[NetworkPolicyEngine] = None

def get_policy_engine() -> NetworkPolicyEngine:
    """Get or create global policy engine singleton"""
    global _policy_engine
    if _policy_engine is None:
        from .config import settings
        _policy_engine = NetworkPolicyEngine(
            audit_log_path=settings.network_audit_log_file
        )
        _init_default_policies(_policy_engine)
    return _policy_engine

def _init_default_policies(engine: NetworkPolicyEngine) -> None:
    """Initialize default security policies"""
    from .config import settings

    # Add operator-configured denylist (always enforced)
    for cidr in settings.network_denylist:
        try:
            engine.add_deny_rule(cidr, reason="Operator configured denylist")
        except ValueError:
            logger.warning(f"Skipping invalid denylist CIDR: {cidr}")

    # Add operator-configured allowlist
    for cidr in settings.network_allowlist:
        try:
            engine.add_allow_rule(cidr, reason="Operator configured allowlist")
        except ValueError:
            logger.warning(f"Skipping invalid allowlist CIDR: {cidr}")

    # When no explicit allowlist is configured, allow public egress while still
    # blocking denylisted ranges (private, metadata, loopback, link-local, ULA).
    # The denylist is checked first (step 1 in check_access), so these implicit
    # allow rules never override an explicit deny.
    if not settings.network_allowlist:
        engine.add_allow_rule(
            "0.0.0.0/0",
            reason="Default public egress (no explicit allowlist configured)",
        )
        engine.add_allow_rule(
            "::/0",
            reason="Default public egress (no explicit allowlist configured)",
        )
        logger.info(
            "No SECUSCAN_NETWORK_ALLOWLIST configured. Default policy: public egress "
            "allowed; denylisted ranges (private, metadata, loopback, link-local, ULA) "
            "still blocked."
        )
    else:
        logger.info(
            "Custom network allowlist configured with %d entries. "
            "Deny-by-default egress policy is active.",
            len(settings.network_allowlist),
        )
