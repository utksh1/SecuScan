"""
Unit tests for backend.secuscan.sandbox_executor pure helper functions.

Covers:
- resolve_sandbox_config returns global defaults when plugin_sandbox is None
- resolve_sandbox_config merges per-plugin overrides with global settings
- classify_memory_violation returns True for SIGSEGV exit codes (-11, 139)
- classify_memory_violation returns True for MemoryError/Cannot allocate memory in stderr
- classify_memory_violation returns True when RSS >= 95% of limit and exit code is non-zero
- classify_memory_violation returns False for normal exit (code 0) even with high RSS
- classify_memory_violation returns False for non-memory errors
"""

import pytest

from backend.secuscan.models import SandboxConfig


class TestResolveSandboxConfig:
    def test_returns_global_defaults_when_no_plugin_sandbox(self):
        """When plugin_sandbox is None, global settings are returned."""
        from backend.secuscan.sandbox_executor import resolve_sandbox_config
        result = resolve_sandbox_config(None)

        assert isinstance(result, SandboxConfig)
        assert hasattr(result, "timeout_seconds")
        assert hasattr(result, "max_memory_mb")
        assert hasattr(result, "max_output_bytes")
        assert hasattr(result, "allow_network")

    def test_merges_per_plugin_overrides(self):
        """Per-plugin overrides take precedence over global defaults."""
        from backend.secuscan.sandbox_executor import resolve_sandbox_config

        plugin_override = SandboxConfig(
            timeout_seconds=120,
            max_memory_mb=512,
        )
        result = resolve_sandbox_config(plugin_override)

        # Overridden fields reflect the plugin value
        assert result.timeout_seconds == 120
        assert result.max_memory_mb == 512
        # Non-overridden fields retain global defaults
        assert hasattr(result, "max_output_bytes")
        assert hasattr(result, "allow_network")

    def test_only_specified_fields_are_overridden(self):
        """Only the fields specified in plugin_override are changed; others use global."""
        from backend.secuscan.sandbox_executor import resolve_sandbox_config

        plugin_override = SandboxConfig(
            max_memory_mb=256,
        )
        result = resolve_sandbox_config(plugin_override)

        assert result.max_memory_mb == 256
        # timeout_seconds and other fields come from global settings
        assert hasattr(result, "timeout_seconds")
        assert result.timeout_seconds != 256  # should be the global value


class TestClassifyMemoryViolation:
    def test_sigsegv_exit_code(self):
        """Exit code -11 (SIGSEGV) is classified as memory violation."""
        from backend.secuscan.sandbox_executor import classify_memory_violation

        assert classify_memory_violation(-11, "", 0, 0) is True

    def test_sigsegv_139(self):
        """Exit code 139 (= 128 + 11 = SIGSEGV) is classified as memory violation."""
        from backend.secuscan.sandbox_executor import classify_memory_violation

        assert classify_memory_violation(139, "", 0, 0) is True

    def test_memory_error_in_stderr(self):
        """'MemoryError' in stderr triggers memory violation classification."""
        from backend.secuscan.sandbox_executor import classify_memory_violation

        assert classify_memory_violation(1, "Python: MemoryError: out of memory", 0, 0) is True

    def test_cannot_allocate_memory_in_stderr(self):
        """'Cannot allocate memory' in stderr triggers memory violation."""
        from backend.secuscan.sandbox_executor import classify_memory_violation

        assert classify_memory_violation(1, "bash: Cannot allocate memory", 0, 0) is True

    def test_rss_over_95_percent_with_nonzero_exit(self):
        """RSS >= 95% of limit with non-zero exit code is classified as memory violation."""
        from backend.secuscan.sandbox_executor import classify_memory_violation

        limit = 1000
        # Exactly 95% triggers
        assert classify_memory_violation(1, "", 950, limit) is True
        # Above 95% also triggers
        assert classify_memory_violation(42, "", 960, limit) is True

    def test_rss_below_95_percent_with_nonzero_exit(self):
        """RSS below 95% of limit does not trigger the RSS-based classification."""
        from backend.secuscan.sandbox_executor import classify_memory_violation

        limit = 1000
        # 94% does not trigger RSS-based classification (but exit code is non-zero)
        # This returns False because 940 < 950 (95% of 1000)
        assert classify_memory_violation(1, "", 940, limit) is False

    def test_zero_exit_with_high_rss_is_not_violation(self):
        """Exit code 0 with high RSS is NOT a memory violation."""
        from backend.secuscan.sandbox_executor import classify_memory_violation

        assert classify_memory_violation(0, "", 1_000_000_000, 1_000_000_000) is False

    def test_non_memory_error_with_normal_exit(self):
        """Non-zero exit code without memory indicators is not a memory violation."""
        from backend.secuscan.sandbox_executor import classify_memory_violation

        # Regular error, not memory related
        assert classify_memory_violation(2, "Plugin not found: unknown-plugin", 100, 1000) is False
        # High RSS but clean exit (0) and no stderr keywords
        assert classify_memory_violation(0, "some generic error", 950, 1000) is False
