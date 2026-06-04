"""
Per-plugin capability declarations and pre-execution enforcement.

Plugins declare a list of capabilities they require in their metadata.json under
the ``capabilities`` key.  The enforcer checks that list against the operator's
``denied_capabilities`` setting (``SECUSCAN_DENIED_CAPABILITIES`` env var, comma-
separated) before any command is built or process is spawned.

Supported capabilities
----------------------
network       - plugin makes outbound network connections
filesystem    - plugin reads or writes paths on the local filesystem
docker        - plugin requires the Docker daemon at runtime
credentials   - plugin pulls secrets from the credential vault
intrusive     - plugin performs active probing that may affect target systems
exploit       - plugin attempts to exploit vulnerabilities (highest risk, opt-in only)

Backward compatibility / migration
-----------------------------------
Plugins that do **not** declare a ``capabilities`` list (i.e. all plugins that
pre-date this feature) are **not broken**.  Instead, an implied capability set is
derived from their ``safety.level`` field:

  safe      → ["network"]
  intrusive → ["network", "intrusive"]
  exploit   → ["network", "intrusive", "exploit"]

This means:

* Existing plugins without a ``capabilities`` field continue to load and execute
  normally.  No plugin metadata files need to be updated for the enforcement
  system to become active.
* Operators can still deny capabilities (e.g. ``SECUSCAN_DENIED_CAPABILITIES=exploit``)
  and all exploit-level plugins will be blocked even if they lack an explicit
  ``capabilities`` declaration.
* Plugin authors are encouraged to add an explicit ``capabilities`` list to their
  metadata.json so operators have fine-grained visibility.  After adding or
  changing the ``capabilities`` field the plugin checksum must be regenerated
  (run ``python -m backend.secuscan.plugins_validate --refresh <plugin-id>``).
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, List, Optional, Set

import logging

logger = logging.getLogger(__name__)


class Capability(str, Enum):
    """All recognised plugin capability tokens."""

    NETWORK = "network"
    FILESYSTEM = "filesystem"
    DOCKER = "docker"
    CREDENTIALS = "credentials"
    INTRUSIVE = "intrusive"
    EXPLOIT = "exploit"


ALL_CAPABILITIES: FrozenSet[str] = frozenset(c.value for c in Capability)

# Capabilities that are implicitly required by a plugin's safety level when the
# plugin has not declared them explicitly.  This lets older plugins without a
# ``capabilities`` field degrade gracefully while still being enforceable.
_SAFETY_LEVEL_IMPLIED: dict[str, List[str]] = {
    "safe": ["network"],
    "intrusive": ["network", "intrusive"],
    "exploit": ["network", "intrusive", "exploit"],
}


class CapabilityDeniedError(PermissionError):
    """Raised when a plugin attempts to use a capability that the operator has denied."""

    def __init__(self, plugin_id: str, denied: Set[str]) -> None:
        self.plugin_id = plugin_id
        self.denied_capabilities = denied
        caps = ", ".join(sorted(denied))
        super().__init__(
            f"Plugin '{plugin_id}' requires capabilities [{caps}] that are denied by "
            "operator policy. Update SECUSCAN_DENIED_CAPABILITIES to allow them or "
            "choose a plugin that does not require these capabilities."
        )


def validate_capability_list(capabilities: List[str], plugin_id: str) -> List[str]:
    """Return the normalised capability list, raising ValueError for unknowns."""
    normalised: List[str] = []
    for raw in capabilities:
        token = raw.strip().lower()
        if token not in ALL_CAPABILITIES:
            raise ValueError(
                f"Plugin '{plugin_id}' declares unknown capability '{raw}'. "
                f"Supported capabilities: {sorted(ALL_CAPABILITIES)}"
            )
        normalised.append(token)
    return normalised


def effective_capabilities(
    declared: Optional[List[str]],
    safety_level: str,
    plugin_id: str,
) -> Set[str]:
    """Combine explicitly declared capabilities with safety-level implied ones.

    If the plugin declares an explicit capability list, that list is the source
    of truth (implied capabilities are *not* added on top — they were already
    considered by the plugin author).  If no capabilities are declared at all the
    implied set for the plugin's safety level is used so that legacy plugins
    remain enforceable.
    """
    if declared is not None and len(declared) > 0:
        validated = validate_capability_list(declared, plugin_id)
        return set(validated)

    implied = _SAFETY_LEVEL_IMPLIED.get(safety_level, ["network"])
    return set(implied)


class CapabilityEnforcer:
    """Checks plugin capabilities against the operator-configured denied set.

    Instantiate once and reuse across the application lifetime.  The denied set
    is fixed at construction time so that the enforcer is deterministic and
    testable independently of the global settings object.
    """

    def __init__(self, denied_capabilities: Optional[List[str]] = None) -> None:
        raw = denied_capabilities or []
        normalised: List[str] = []
        unknown: List[str] = []
        for tok in raw:
            token = tok.strip().lower()
            if not token:
                continue
            if token not in ALL_CAPABILITIES:
                unknown.append(tok.strip())
            else:
                normalised.append(token)
        if unknown:
            raise ValueError(
                f"SECUSCAN_DENIED_CAPABILITIES contains unrecognised capability tokens: "
                f"{unknown!r}. Supported capabilities: {sorted(ALL_CAPABILITIES)}. "
                "Fix the typo or remove the unknown token — a misconfigured deny-list "
                "silently fails to enforce the intended policy."
            )
        self._denied: FrozenSet[str] = frozenset(normalised)
        if self._denied:
            logger.info(
                "CapabilityEnforcer: operator has denied capabilities: %s",
                sorted(self._denied),
            )

    @property
    def denied(self) -> FrozenSet[str]:
        return self._denied

    def check(
        self,
        plugin_id: str,
        declared: Optional[List[str]],
        safety_level: str,
    ) -> None:
        """Raise CapabilityDeniedError if the plugin needs a denied capability.

        Args:
            plugin_id:    The plugin's ``id`` field from metadata.
            declared:     The ``capabilities`` list from the plugin's metadata (may be None).
            safety_level: The plugin's safety level (``safe``, ``intrusive``, ``exploit``).

        Raises:
            CapabilityDeniedError: when any required capability is denied.
        """
        if not self._denied:
            return

        required = effective_capabilities(declared, safety_level, plugin_id)
        blocked = required & self._denied

        if blocked:
            logger.warning(
                "Blocked plugin '%s': requires denied capabilities %s",
                plugin_id,
                sorted(blocked),
            )
            raise CapabilityDeniedError(plugin_id, blocked)

        logger.debug(
            "Capability check passed for plugin '%s': required=%s",
            plugin_id,
            sorted(required),
        )


def build_enforcer_from_settings() -> CapabilityEnforcer:
    """Construct a CapabilityEnforcer from the global application settings."""
    from .config import settings  # local import to avoid circular dependency

    return CapabilityEnforcer(denied_capabilities=list(settings.denied_capabilities))
