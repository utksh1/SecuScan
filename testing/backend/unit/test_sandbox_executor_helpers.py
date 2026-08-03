"""
Unit tests for classify_memory_violation and resolve_sandbox_config helpers.

Imports the real production functions from backend.secuscan.sandbox_executor
so a regression in the actual implementation is caught by these tests.
"""
import sys
from unittest.mock import patch, MagicMock
from backend.secuscan.sandbox_executor import (
    classify_memory_violation,
    resolve_sandbox_config,
)
from backend.secuscan.models import SandboxConfig


# ---------------------------------------------------------------------------
# classify_memory_violation
# ---------------------------------------------------------------------------


def test_sigsegv_exit_code_minus11():
    """SIGSEGV exit code (-11) triggers memory violation classification."""
    assert classify_memory_violation(-11, "", 0, 0) is True


def test_sigsegv_exit_code_139():
    """Exit code 139 (=128+11, SIGSEGV on many systems) triggers classification."""
    assert classify_memory_violation(139, "", 0, 0) is True


def test_memory_error_in_stderr():
    """MemoryError in stderr triggers memory violation classification."""
    assert classify_memory_violation(0, "Python: MemoryError: cannot allocate", 0, 0) is True


def test_cannot_allocate_in_stderr():
    """Cannot allocate message in stderr triggers memory violation classification."""
    assert classify_memory_violation(1, "Error: Cannot allocate memory", 0, 0) is True


def test_rss_at_95_percent_with_failure():
    """RSS at or above 95% of limit combined with non-zero exit is classified as memory violation."""
    limit = 100_000_000
    rss_at_95 = limit * 95 // 100
    assert classify_memory_violation(1, "", rss_at_95, limit) is True


def test_rss_at_94_percent_with_failure():
    """RSS at 94% of limit with non-zero exit is NOT classified as memory violation."""
    limit = 100_000_000
    rss_at_94 = limit * 94 // 100
    assert classify_memory_violation(1, "", rss_at_94, limit) is False


def test_rss_at_95_percent_with_zero_exit():
    """RSS at 95% with exit code 0 is not classified as memory violation."""
    limit = 100_000_000
    rss_at_95 = limit * 95 // 100
    assert classify_memory_violation(0, "", rss_at_95, limit) is False


def test_clean_exit_not_memory_violation():
    """Clean exit (code 0) with no error message is not a memory violation."""
    assert classify_memory_violation(0, "All good", 50_000_000, 100_000_000) is False


def test_unrelated_error_not_memory_violation():
    """Unrelated error messages do not trigger memory violation classification."""
    assert classify_memory_violation(1, "File not found", 10_000_000, 100_000_000) is False


# ---------------------------------------------------------------------------
# resolve_sandbox_config
# ---------------------------------------------------------------------------


def test_resolve_sandbox_config_no_override():
    """Without plugin overrides, base settings values are used."""
    base = SandboxConfig(timeout_seconds=600, max_memory_mb=512, allow_network=True)
    result = resolve_sandbox_config(None)
    assert result.timeout_seconds == 600
    assert result.max_memory_mb == 512
    assert result.allow_network is True


def test_resolve_sandbox_config_partial_override():
    """Per-plugin overrides replace only the specified fields."""
    override = SandboxConfig(timeout_seconds=300)
    result = resolve_sandbox_config(override)
    # Overridden
    assert result.timeout_seconds == 300
    # From base
    assert result.max_memory_mb == 512


def test_resolve_sandbox_config_all_fields_overridden():
    """All fields can be overridden by plugin config."""
    override = SandboxConfig(
        timeout_seconds=120,
        max_memory_mb=256,
        allow_network=False,
    )
    result = resolve_sandbox_config(override)
    assert result.timeout_seconds == 120
    assert result.max_memory_mb == 256
    assert result.allow_network is False


def test_resolve_sandbox_config_max_output_bytes():
    """max_output_bytes is included in the merge."""
    override = SandboxConfig(max_output_bytes=1024)
    result = resolve_sandbox_config(override)
    assert result.max_output_bytes == 1024
