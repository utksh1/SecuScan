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
    if declared is not None and len(declared) > 0:
        validated = validate_capability_list(declared, plugin_id)
        return set(validated)

    implied = _SAFETY_LEVEL_IMPLIED.get(safety_level, ["network"])
    return set(implied)


class CapabilityEnforcer:
    """Checks plugin capabilities against the operator-configured denied set.
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
    from .config import settings

    return CapabilityEnforcer(denied_capabilities=list(settings.denied_capabilities))
