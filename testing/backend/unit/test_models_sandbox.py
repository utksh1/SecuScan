"""
Unit tests for SandboxConfig and SandboxViolation in backend/secuscan/models.py.
"""

from __future__ import annotations

import pytest

from backend.secuscan.models import (
    SandboxConfig,
    SandboxViolation,
)


# ---------------------------------------------------------------------------
# SandboxConfig
# ---------------------------------------------------------------------------


class TestSandboxConfigDefaults:
    def test_default_timeout_seconds(self):
        config = SandboxConfig()
        assert config.timeout_seconds == 120

    def test_default_max_memory_mb(self):
        config = SandboxConfig()
        assert config.max_memory_mb == 512

    def test_default_max_output_bytes(self):
        config = SandboxConfig()
        assert config.max_output_bytes == 5_242_880

    def test_default_allow_network(self):
        config = SandboxConfig()
        assert config.allow_network is True


class TestSandboxConfigOverrides:
    def test_custom_timeout_seconds(self):
        config = SandboxConfig(timeout_seconds=600)
        assert config.timeout_seconds == 600

    def test_custom_max_memory_mb(self):
        config = SandboxConfig(max_memory_mb=1024)
        assert config.max_memory_mb == 1024

    def test_custom_max_output_bytes(self):
        config = SandboxConfig(max_output_bytes=20_000_000)
        assert config.max_output_bytes == 20_000_000

    def test_custom_allow_network(self):
        config = SandboxConfig(allow_network=False)
        assert config.allow_network is False

    def test_all_fields_custom(self):
        config = SandboxConfig(
            timeout_seconds=300,
            max_memory_mb=256,
            max_output_bytes=10_000_000,
            allow_network=False,
        )
        assert config.timeout_seconds == 300
        assert config.max_memory_mb == 256
        assert config.max_output_bytes == 10_000_000
        assert config.allow_network is False


# ---------------------------------------------------------------------------
# SandboxViolation
# ---------------------------------------------------------------------------


class TestSandboxViolation:
    def test_raises_with_reason(self):
        exc = SandboxViolation("memory limit exceeded")
        assert str(exc) == "memory limit exceeded"

    def test_reason_attribute_is_accessible(self):
        exc = SandboxViolation("CPU time limit exceeded")
        assert exc.reason == "CPU time limit exceeded"

    def test_inherits_from_exception(self):
        exc = SandboxViolation("test")
        assert isinstance(exc, Exception)

    def test_empty_reason(self):
        exc = SandboxViolation("")
        assert str(exc) == ""
        assert exc.reason == ""

    def test_unicode_reason(self):
        exc = SandboxViolation("memory limit exceeded: 5MB")
        assert exc.reason == "memory limit exceeded: 5MB"
