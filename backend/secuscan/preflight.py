"""
preflight.py — Plugin dependency preflight checks with OS-specific guidance.

Detects missing binaries and Python packages required by a plugin and returns
actionable install instructions tailored to the host operating system.

Design goals
------------
* Pure functions — no I/O side-effects beyond shutil.which / importlib.
* OS detection is injected so callers (and tests) can override it easily.
* Guidance strings are short and copy-pasteable, not prose paragraphs.
"""

from __future__ import annotations

import importlib.util
import platform
import shutil
from dataclasses import dataclass, field
from typing import Callable, List, Optional


# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------

def _current_os() -> str:
    """Return a normalised OS tag: 'linux', 'macos', or 'windows'."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "linux"


# ---------------------------------------------------------------------------
# Install hint database
# ---------------------------------------------------------------------------

_BINARY_HINTS: dict[str, dict[str, str]] = {
    "nmap": {
        "linux":  "sudo apt-get install -y nmap",
        "macos":  "brew install nmap",
    },
    "nikto": {
        "linux":  "sudo apt-get install -y nikto",
        "macos":  "brew install nikto",
    },
    "subfinder": {
        "linux":  "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        "macos":  "brew install subfinder",
    },
    "dnsrecon": {
        "linux":  "sudo apt-get install -y dnsrecon",
        "macos":  "pip3 install dnsrecon",
    },
    "dnsx": {
        "linux":  "go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
        "macos":  "brew install dnsx",
    },
    "httpx": {
        "linux":  "go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest",
        "macos":  "brew install httpx",
    },
    "nuclei": {
        "linux":  "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        "macos":  "brew install nuclei",
    },
    "amass": {
        "linux":  "go install -v github.com/owasp-amass/amass/v4/...@master",
        "macos":  "brew install amass",
    },
    "katana": {
        "linux":  "go install -v github.com/projectdiscovery/katana/cmd/katana@latest",
        "macos":  "brew install katana",
    },
    "ffuf": {
        "linux":  "sudo apt-get install -y ffuf",
        "macos":  "brew install ffuf",
    },
    "gobuster": {
        "linux":  "sudo apt-get install -y gobuster",
        "macos":  "brew install gobuster",
    },
    "sqlmap": {
        "linux":  "sudo apt-get install -y sqlmap",
        "macos":  "brew install sqlmap",
    },
    "wpscan": {
        "linux":  "sudo apt-get install -y wpscan",
        "macos":  "brew install wpscan",
    },
    "curl": {
        "linux":  "sudo apt-get install -y curl",
        "macos":  "brew install curl",
    },
    "wget": {
        "linux":  "sudo apt-get install -y wget",
        "macos":  "brew install wget",
    },
    "whois": {
        "linux":  "sudo apt-get install -y whois",
        "macos":  "brew install whois",
    },
    "uncover": {
        "linux":  "go install -v github.com/projectdiscovery/uncover/cmd/uncover@latest",
        "macos":  "brew install uncover",
    },
}


def _install_hint(binary: str, os_tag: str) -> Optional[str]:
    """Return the install command for *binary* on *os_tag*, or None if unknown."""
    return _BINARY_HINTS.get(binary, {}).get(os_tag)


# ---------------------------------------------------------------------------
# Core dataclass
# ---------------------------------------------------------------------------

@dataclass
class PreflightResult:
    """Outcome of a plugin dependency preflight check."""

    runnable: bool
    missing_binaries: List[str] = field(default_factory=list)
    missing_packages: List[str] = field(default_factory=list)
    install_guidance: Optional[str] = None

    @property
    def status(self) -> str:
        return "available" if self.runnable else "unavailable"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_plugin_dependencies(
    engine: dict,
    dependencies: Optional[dict],
    *,
    os_tag: Optional[str] = None,
    which_fn: Callable[[str], Optional[str]] = shutil.which,
    import_fn: Callable[[str], Optional[object]] = importlib.util.find_spec,
) -> PreflightResult:
    """
    Check whether all runtime dependencies declared by a plugin are satisfied.

    Args:
        engine:       Plugin engine dict e.g. {"type": "cli", "binary": "nmap"}.
        dependencies: Plugin dependencies dict or None
                      e.g. {"binaries": [...], "python_packages": [...]}
        os_tag:       Override OS detection — "linux", "macos", or "windows".
                      Defaults to the current host OS.
        which_fn:     Callable used to locate binaries (injectable for tests).
        import_fn:    Callable used to locate Python packages (injectable).

    Returns:
        A PreflightResult describing readiness and actionable guidance.
    """
    os_tag = os_tag or _current_os()

    # ── Collect required binaries ──────────────────────────────────────────
    required_binaries: list[str] = []
    if engine.get("type") == "cli":
        b = engine.get("binary")
        if b:
            required_binaries.append(b)

    if isinstance(dependencies, dict):
        for b in dependencies.get("binaries") or []:
            if isinstance(b, str) and b.strip():
                required_binaries.append(b)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_binaries: list[str] = []
    for b in required_binaries:
        if b not in seen:
            seen.add(b)
            unique_binaries.append(b)

    missing_binaries = [b for b in unique_binaries if which_fn(b) is None]

    # ── Collect required Python packages ──────────────────────────────────
    required_packages: list[str] = []
    if isinstance(dependencies, dict):
        for pkg in dependencies.get("python_packages") or []:
            if isinstance(pkg, str) and pkg.strip():
                required_packages.append(pkg)

    missing_packages = [pkg for pkg in required_packages if import_fn(pkg) is None]

    # ── Build guidance string ─────────────────────────────────────────────
    runnable = not missing_binaries and not missing_packages
    guidance: Optional[str] = None

    if not runnable:
        parts: list[str] = []

        for binary in missing_binaries:
            hint = _install_hint(binary, os_tag)
            if hint:
                parts.append(hint)
            else:
                parts.append(f"# install '{binary}' manually (no known package for {os_tag})")

        for pkg in missing_packages:
            parts.append(f"pip install {pkg}")

        guidance = "\n".join(parts)

    return PreflightResult(
        runnable=runnable,
        missing_binaries=missing_binaries,
        missing_packages=missing_packages,
        install_guidance=guidance,
    )