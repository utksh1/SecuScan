"""
Unit tests for sandbox_executor.py pure helper functions.
"""
import pytest

from backend.secuscan.sandbox_executor import (
    resolve_sandbox_config,
    classify_memory_violation,
)
from backend.secuscan.models import SandboxConfig


class TestResolveSandboxConfig:
    def test_returns_base_config_when_no_override(self):
        config = resolve_sandbox_config(plugin_sandbox=None)
        assert isinstance(config, SandboxConfig)
        assert config.timeout_seconds is not None
        assert config.max_memory_mb > 0

    def test_applies_plugin_override_all_fields(self):
        override = SandboxConfig(timeout_seconds=999, max_memory_mb=2048)
        config = resolve_sandbox_config(plugin_sandbox=override)
        assert config.timeout_seconds == 999
        assert config.max_memory_mb == 2048

    def test_partial_override_preserves_unset_base_fields(self):
        override = SandboxConfig(timeout_seconds=300)
        config = resolve_sandbox_config(plugin_sandbox=override)
        assert config.timeout_seconds == 300
        # max_memory_mb and other base fields still populated from settings
        assert config.max_memory_mb > 0
        assert config.allow_network is not None


class TestClassifyMemoryViolation:
    def test_sigsegv_exit_code(self):
        # exit code 139 = 128 + 11 (SIGSEGV) — strong indicator of memory exhaustion
        assert classify_memory_violation(139, "", 0, 100_000_000) is True

    def test_sigabrt_exit_code(self):
        # SIGABRT is not a memory signal
        assert classify_memory_violation(134, "", 0, 100_000_000) is False

    def test_memory_error_string(self):
        assert classify_memory_violation(1, "MemoryError: out of memory", 0, 100_000_000) is True

    def test_cannot_allocate_string(self):
        assert classify_memory_violation(1, "Cannot allocate memory", 0, 100_000_000) is True

    def test_rss_near_limit_and_nonzero_exit(self):
        limit = 100_000_000
        # RSS at 96% of limit with non-zero exit
        assert classify_memory_violation(1, "", limit * 96 // 100, limit) is True

    def test_rss_below_limit_passes(self):
        limit = 100_000_000
        assert classify_memory_violation(1, "", limit * 50 // 100, limit) is False

    def test_rss_at_95_percent_boundary(self):
        limit = 100_000_000
        # At exactly 95%, it IS classified as violation (threshold is >= 95%)
        assert classify_memory_violation(1, "", limit * 95 // 100, limit) is True

    def test_zero_exit_with_clean_stderr_passes(self):
        # Exit 0 with no memory-error indicators in stderr is not a violation
        limit = 1_000_000
        assert classify_memory_violation(0, "", limit * 99 // 100, limit) is False

    def test_exit_1_above_95_percent_rss(self):
        limit = 200_000_000
        assert classify_memory_violation(1, "", limit * 96 // 100, limit) is True

    def test_generic_error_string_ignored(self):
        assert classify_memory_violation(1, "Something went wrong", 0, 100_000_000) is False
