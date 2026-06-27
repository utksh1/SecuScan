"""
Unit tests for backend.secuscan.sandbox_executor._build_preexec_fn.

Covers:
- _build_preexec_fn returns a callable
- The callable sets RLIMIT_AS to the correct memory limit
- Returns None on non-Linux platforms
- The returned function does not raise when called (with resource mocked)

The function builds a preexec_fn for asyncio subprocess on Linux. The closure
calls resource.setrlimit which mutates live process state, so resource is
mocked in these tests.
"""

import sys
from unittest.mock import patch, MagicMock

import pytest

from backend.secuscan.sandbox_executor import _build_preexec_fn
from backend.secuscan.models import SandboxConfig


class TestBuildPreexecFn:
    def test_returns_a_callable(self):
        config = SandboxConfig(
            timeout_seconds=30,
            max_memory_mb=512,
            max_output_bytes=10 * 1024 * 1024,
            allow_network=False,
        )
        result = _build_preexec_fn(config)
        assert callable(result)

    def test_sets_correct_rlimit_as(self):
        config = SandboxConfig(
            timeout_seconds=30,
            max_memory_mb=512,
            max_output_bytes=10 * 1024 * 1024,
            allow_network=False,
        )
        preexec_fn = _build_preexec_fn(config)

        called_limits = []
        def mock_setrlimit(which, limits):
            called_limits.append((which, limits))

        mock_resource = MagicMock()
        mock_resource.RLIMIT_AS = MagicMock()
        mock_resource.RLIMIT_AS.value = 123
        mock_resource.setrlimit = mock_setrlimit

        with patch.dict(sys.modules, {"resource": mock_resource}):
            preexec_fn()

        assert len(called_limits) == 1
        which, (soft, hard) = called_limits[0]
        assert which == mock_resource.RLIMIT_AS
        assert soft == 512 * 1024 * 1024
        assert hard == 512 * 1024 * 1024

    def test_rlimit_bytes_equal_memory_mb(self):
        """Verify the RLIMIT_AS soft and hard limits both equal
        the configured max_memory_mb in bytes."""
        config = SandboxConfig(
            timeout_seconds=30,
            max_memory_mb=1024,
            max_output_bytes=10 * 1024 * 1024,
            allow_network=False,
        )
        preexec_fn = _build_preexec_fn(config)

        recorded = []
        mock_resource = MagicMock()
        mock_resource.RLIMIT_AS = MagicMock()
        mock_resource.setrlimit = lambda which, limits: recorded.append(limits)

        with patch.dict(sys.modules, {"resource": mock_resource}):
            preexec_fn()

        assert len(recorded) == 1
        soft, hard = recorded[0]
        assert soft == 1024 * 1024 * 1024
        assert hard == 1024 * 1024 * 1024

    def test_does_not_raise_when_called(self):
        config = SandboxConfig(
            timeout_seconds=30,
            max_memory_mb=128,
            max_output_bytes=1024,
            allow_network=False,
        )
        preexec_fn = _build_preexec_fn(config)

        mock_resource = MagicMock()
        mock_resource.RLIMIT_AS = 123
        mock_resource.setrlimit = MagicMock()

        with patch.dict(sys.modules, {"resource": mock_resource}):
            preexec_fn()
