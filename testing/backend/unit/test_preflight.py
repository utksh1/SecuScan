"""
Unit tests for backend/secuscan/preflight.py

Covers:
- runnable vs unavailable states
- OS-specific install guidance (linux / macos)
- missing binaries + missing python packages
- unknown binary fallback message
- dependency-free plugins
- injection of which_fn / import_fn for hermetic testing
"""

import pytest
from backend.secuscan.preflight import (
    PreflightResult,
    check_plugin_dependencies,
    _current_os,
    _install_hint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _which_all(binary: str):
    """Simulate every binary being present."""
    return f"/usr/bin/{binary}"


def _which_none(binary: str):
    """Simulate no binary being present."""
    return None


def _which_missing(*missing):
    """Return a which_fn that marks specific binaries as absent."""
    missing_set = set(missing)
    def _fn(binary: str):
        return None if binary in missing_set else f"/usr/bin/{binary}"
    return _fn


def _import_all(name: str):
    """Simulate every Python package being importable."""
    return object()


def _import_none(name: str):
    """Simulate no Python package being importable."""
    return None


def _import_missing(*missing):
    missing_set = set(missing)
    def _fn(name: str):
        return None if name in missing_set else object()
    return _fn


# ---------------------------------------------------------------------------
# _current_os
# ---------------------------------------------------------------------------

def test_current_os_returns_known_tag():
    tag = _current_os()
    assert tag in {"linux", "macos", "windows"}


# ---------------------------------------------------------------------------
# _install_hint
# ---------------------------------------------------------------------------

class TestInstallHint:
    def test_nmap_linux(self):
        hint = _install_hint("nmap", "linux")
        assert hint is not None
        assert "apt" in hint
        assert "nmap" in hint

    def test_nmap_macos(self):
        hint = _install_hint("nmap", "macos")
        assert hint is not None
        assert "brew" in hint
        assert "nmap" in hint

    def test_subfinder_linux_uses_go_install(self):
        hint = _install_hint("subfinder", "linux")
        assert hint is not None
        assert "go install" in hint

    def test_subfinder_macos_uses_brew(self):
        hint = _install_hint("subfinder", "macos")
        assert hint is not None
        assert "brew" in hint

    def test_unknown_binary_returns_none(self):
        assert _install_hint("nonexistent_tool_xyz", "linux") is None

    def test_unknown_os_returns_none(self):
        assert _install_hint("nmap", "freebsd") is None


# ---------------------------------------------------------------------------
# check_plugin_dependencies — runnable plugin
# ---------------------------------------------------------------------------

class TestRunnablePlugin:
    def test_cli_plugin_all_binaries_present(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "nmap"},
            dependencies=None,
            which_fn=_which_all,
        )
        assert result.runnable is True
        assert result.status == "available"
        assert result.missing_binaries == []
        assert result.missing_packages == []
        assert result.install_guidance is None

    def test_python_plugin_no_binaries_needed(self):
        result = check_plugin_dependencies(
            engine={"type": "python"},
            dependencies=None,
            which_fn=_which_none,
        )
        assert result.runnable is True

    def test_docker_plugin_no_binary_check(self):
        result = check_plugin_dependencies(
            engine={"type": "docker", "image": "secuscan/scanner:latest"},
            dependencies=None,
            which_fn=_which_none,
        )
        assert result.runnable is True

    def test_no_dependencies_field(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "curl"},
            dependencies=None,
            which_fn=_which_all,
        )
        assert result.runnable is True

    def test_empty_dependencies_dict(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "curl"},
            dependencies={"binaries": [], "python_packages": []},
            which_fn=_which_all,
        )
        assert result.runnable is True


# ---------------------------------------------------------------------------
# check_plugin_dependencies — missing binaries
# ---------------------------------------------------------------------------

class TestMissingBinaries:
    def test_single_missing_binary(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "nmap"},
            dependencies=None,
            os_tag="linux",
            which_fn=_which_none,
        )
        assert result.runnable is False
        assert result.status == "unavailable"
        assert "nmap" in result.missing_binaries

    def test_multiple_missing_binaries(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "subfinder"},
            dependencies={"binaries": ["dnsrecon"]},
            os_tag="linux",
            which_fn=_which_none,
        )
        assert "subfinder" in result.missing_binaries
        assert "dnsrecon" in result.missing_binaries

    def test_partial_missing(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "nmap"},
            dependencies={"binaries": ["subfinder"]},
            os_tag="linux",
            which_fn=_which_missing("subfinder"),
        )
        assert result.runnable is False
        assert "subfinder" in result.missing_binaries
        assert "nmap" not in result.missing_binaries

    def test_duplicate_binary_only_reported_once(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "nmap"},
            dependencies={"binaries": ["nmap"]},
            os_tag="linux",
            which_fn=_which_none,
        )
        assert result.missing_binaries.count("nmap") == 1


# ---------------------------------------------------------------------------
# check_plugin_dependencies — OS-specific guidance
# ---------------------------------------------------------------------------

class TestInstallGuidance:
    def test_linux_guidance_uses_apt(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "nmap"},
            dependencies=None,
            os_tag="linux",
            which_fn=_which_none,
        )
        assert result.install_guidance is not None
        assert "apt" in result.install_guidance
        assert "nmap" in result.install_guidance

    def test_macos_guidance_uses_brew(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "nmap"},
            dependencies=None,
            os_tag="macos",
            which_fn=_which_none,
        )
        assert result.install_guidance is not None
        assert "brew" in result.install_guidance
        assert "nmap" in result.install_guidance

    def test_unknown_binary_fallback_message(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "my_custom_tool"},
            dependencies=None,
            os_tag="linux",
            which_fn=_which_none,
        )
        assert result.install_guidance is not None
        assert "my_custom_tool" in result.install_guidance
        assert "manually" in result.install_guidance

    def test_multiple_binaries_guidance_has_all_commands(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "nmap"},
            dependencies={"binaries": ["nikto"]},
            os_tag="linux",
            which_fn=_which_none,
        )
        assert "nmap" in result.install_guidance
        assert "nikto" in result.install_guidance

    def test_no_guidance_when_runnable(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "nmap"},
            dependencies=None,
            os_tag="linux",
            which_fn=_which_all,
        )
        assert result.install_guidance is None


# ---------------------------------------------------------------------------
# check_plugin_dependencies — missing Python packages
# ---------------------------------------------------------------------------

class TestMissingPythonPackages:
    def test_missing_package_detected(self):
        result = check_plugin_dependencies(
            engine={"type": "python"},
            dependencies={"python_packages": ["scapy"]},
            which_fn=_which_all,
            import_fn=_import_none,
        )
        assert result.runnable is False
        assert "scapy" in result.missing_packages

    def test_present_package_not_reported(self):
        result = check_plugin_dependencies(
            engine={"type": "python"},
            dependencies={"python_packages": ["scapy"]},
            which_fn=_which_all,
            import_fn=_import_all,
        )
        assert result.runnable is True
        assert result.missing_packages == []

    def test_package_guidance_uses_pip(self):
        result = check_plugin_dependencies(
            engine={"type": "python"},
            dependencies={"python_packages": ["scapy"]},
            which_fn=_which_all,
            import_fn=_import_none,
        )
        assert result.install_guidance is not None
        assert "pip install scapy" in result.install_guidance

    def test_missing_binary_and_package_both_in_guidance(self):
        result = check_plugin_dependencies(
            engine={"type": "cli", "binary": "nmap"},
            dependencies={"python_packages": ["scapy"]},
            os_tag="linux",
            which_fn=_which_none,
            import_fn=_import_none,
        )
        assert "nmap" in result.install_guidance
        assert "pip install scapy" in result.install_guidance


# ---------------------------------------------------------------------------
# PreflightResult — status property
# ---------------------------------------------------------------------------

class TestPreflightResultStatus:
    def test_runnable_status(self):
        r = PreflightResult(runnable=True)
        assert r.status == "available"

    def test_not_runnable_status(self):
        r = PreflightResult(runnable=False, missing_binaries=["nmap"])
        assert r.status == "unavailable"