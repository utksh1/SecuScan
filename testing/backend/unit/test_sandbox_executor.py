"""
Unit tests for backend.secuscan.sandbox_executor pure helpers.

Covers:
- resolve_sandbox_config returns global defaults when plugin_sandbox is None
- resolve_sandbox_config applies plugin overrides correctly
- classify_memory_violation returns True for SIGSEGV exit codes
- classify_memory_violation returns True for memory error messages
- classify_memory_violation returns True when RSS near limit and exit non-zero
- classify_memory_violation returns False for normal exit
"""

from backend.secuscan.sandbox_executor import resolve_sandbox_config, classify_memory_violation
from backend.secuscan.models import SandboxConfig


class TestResolveSandboxConfig:
    def test_returns_defaults_when_no_override(self):
        """resolve_sandbox_config returns global settings when plugin_sandbox is None."""
        result = resolve_sandbox_config(None)
        assert isinstance(result, SandboxConfig)
        # Verify it is a real SandboxConfig (not None)
        assert result is not None

    def test_applies_timeout_override(self):
        """resolve_sandbox_config overrides timeout when plugin_sandbox provides one."""
        override = SandboxConfig(timeout_seconds=120)
        result = resolve_sandbox_config(override)
        assert result.timeout_seconds == 120

    def test_applies_memory_override(self):
        """resolve_sandbox_config overrides max_memory_mb when plugin_sandbox provides one."""
        override = SandboxConfig(max_memory_mb=512)
        result = resolve_sandbox_config(override)
        assert result.max_memory_mb == 512

    def test_applies_network_override(self):
        """resolve_sandbox_config overrides allow_network when plugin_sandbox provides one."""
        override = SandboxConfig(allow_network=False)
        result = resolve_sandbox_config(override)
        assert result.allow_network is False


class TestClassifyMemoryViolation:
    def test_sigsegv_exit_code_negative_11(self):
        """classify_memory_violation returns True for exit code -11."""
        assert classify_memory_violation(-11, "", 0, 0) is True

    def test_sigsegv_exit_code_139(self):
        """classify_memory_violation returns True for exit code 139."""
        assert classify_memory_violation(139, "", 0, 0) is True

    def test_memory_error_in_stderr(self):
        """classify_memory_violation returns True when stderr contains MemoryError."""
        assert classify_memory_violation(1, "Python: MemoryError", 0, 0) is True

    def test_cannot_allocate_in_stderr(self):
        """classify_memory_violation returns True when stderr contains 'Cannot allocate memory'."""
        assert classify_memory_violation(1, "error: Cannot allocate memory", 0, 0) is True

    def test_rss_near_limit_with_nonzero_exit(self):
        """classify_memory_violation returns True when RSS >= 95% of limit and exit != 0."""
        assert classify_memory_violation(1, "", 950, 1000) is True

    def test_rss_near_limit_with_zero_exit(self):
        """classify_memory_violation returns False when exit code is 0, even if RSS near limit."""
        assert classify_memory_violation(0, "", 950, 1000) is False

    def test_normal_exit_returns_false(self):
        """classify_memory_violation returns False for normal exit with no memory indicators."""
        assert classify_memory_violation(0, "", 100, 1000) is False
