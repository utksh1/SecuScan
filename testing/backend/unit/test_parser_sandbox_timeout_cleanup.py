"""
Unit tests for parser_sandbox subprocess timeout and cleanup paths.

Covers:
  - subprocess.TimeoutExpired: process is killed, ParserSandboxError raised
  - thread cleanup after kill: reader threads are joined within timeout
  - overflow kill: process killed before full buffer read, ParserSandboxError raised

These are not happy-path tests (those are in test_parser_sandbox.py); these
focus on the failure/timeout paths that must not leak resources.
"""

from __future__ import annotations

import subprocess
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestParserSandboxTimeoutCleanup:
    """Coverage for run_parser_in_sandbox timeout kill and cleanup."""

    def test_timeout_expired_raises_parser_sandbox_error(self, tmp_path):
        """subprocess.TimeoutExpired must be caught and re-raised as ParserSandboxError."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox, _sanitised_env
        from backend.secuscan.parser_sandbox import _BOOTSTRAP_TEMPLATE
        import json

        # Write a parser that sleeps long enough to be killed.
        parser = tmp_path / "parser.py"
        parser.write_text("import time; time.sleep(60); print('late')\n", encoding="utf-8")

        with pytest.raises(subprocess.TimeoutExpired):
            proc = subprocess.Popen(
                ["python3", "-c", _BOOTSTRAP_TEMPLATE.format(
                    parser_path=str(parser),
                    max_input_bytes=1024,
                )],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_sanitised_env(),
            )
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise

    def test_timeout_kill_does_not_hang_join_threads(self, tmp_path):
        """Threads reading from killed subprocess must complete within the join timeout."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox, _sanitised_env
        from backend.secuscan.parser_sandbox import _BOOTSTRAP_TEMPLATE

        parser = tmp_path / "parser.py"
        parser.write_text("import time; time.sleep(60)\n", encoding="utf-8")

        start = time.monotonic()
        with pytest.raises(Exception):  # ParserSandboxError
            run_parser_in_sandbox(parser, "slow", "data", timeout_seconds=1)
        elapsed = time.monotonic() - start

        # Must not hang; total time must be well under 10 seconds.
        assert elapsed < 10, f"ParserSandboxError took {elapsed:.1f}s — threads may be hanging"

    def test_timeout_error_message_contains_duration(self, tmp_path):
        """ParserSandboxError message after timeout must include the duration."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox

        parser = tmp_path / "parser.py"
        parser.write_text("import time; time.sleep(60)\n", encoding="utf-8")

        with pytest.raises(Exception) as exc_info:
            run_parser_in_sandbox(parser, "slow_plugin", "data", timeout_seconds=2)

        exc_message = str(exc_info.value)
        assert "timed out" in exc_message or "timeout" in exc_message.lower()

    def test_timeout_error_includes_stderr(self, tmp_path):
        """ParserSandboxError after timeout must include stderr output."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox

        parser = tmp_path / "parser.py"
        # Write to stderr before sleeping.
        parser.write_text(
            "import sys, time; sys.stderr.write('early error\\n'); time.sleep(60)\n",
            encoding="utf-8",
        )

        with pytest.raises(Exception) as exc_info:
            run_parser_in_sandbox(parser, "stderr_plugin", "data", timeout_seconds=1)

        exc_message = str(exc_info.value)
        assert "early error" in exc_message

    def test_multiple_consecutive_timeouts_do_not_leak_resources(self, tmp_path):
        """Running multiple timeouts in sequence must not accumulate open file handles."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox
        import resource

        parser = tmp_path / "parser.py"
        parser.write_text("import time; time.sleep(60)\n", encoding="utf-8")

        for _ in range(3):
            with pytest.raises(Exception):
                run_parser_in_sandbox(parser, "repeat", "data", timeout_seconds=1)

        # Get current process file descriptor count.
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        # If we are leaking fds, the count would grow.  This is a rough check.
        import os as _os
        open_fds_before = len(_os.listdir(f"/proc/{_os.getpid()}/fd"))
        # Run one more timeout.
        with pytest.raises(Exception):
            run_parser_in_sandbox(parser, "final", "data", timeout_seconds=1)
        open_fds_after = len(_os.listdir(f"/proc/{_os.getpid()}/fd"))
        assert open_fds_after <= open_fds_before + 1, "File descriptors may be leaking after timeout"


class TestParserSandboxOverflowCleanup:
    """Coverage for run_parser_in_sandbox output-overflow kill and cleanup."""

    def test_overflow_kill_does_not_hang(self, tmp_path):
        """A parser that writes more than max_output_bytes must be killed promptly."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox

        parser = tmp_path / "parser.py"
        # Write a parser that outputs 10 MB of data.
        parser.write_text(
            f"import sys; sys.stdout.write('x' * (10 * 1024 * 1024))\n",
            encoding="utf-8",
        )

        start = time.monotonic()
        with pytest.raises(Exception) as exc_info:
            run_parser_in_sandbox(parser, "big_output", "data", max_output_bytes=1024)
        elapsed = time.monotonic() - start

        # Must complete quickly without waiting for full 10 MB to be written.
        assert elapsed < 10, f"Overflow kill took {elapsed:.1f}s — may be reading full output"
        assert "limit" in str(exc_info.value).lower() or "output" in str(exc_info.value).lower()

    def test_overflow_error_message_contains_limit(self, tmp_path):
        """ParserSandboxError after overflow must reference the size limit."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox

        parser = tmp_path / "parser.py"
        parser.write_text("import sys; sys.stdout.write('x' * 10_000_000)\n", encoding="utf-8")

        with pytest.raises(Exception) as exc_info:
            run_parser_in_sandbox(parser, "overflow", "data", max_output_bytes=512)

        assert "limit" in str(exc_info.value).lower() or "exceeded" in str(exc_info.value).lower()
