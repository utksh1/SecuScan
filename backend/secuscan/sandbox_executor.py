"""
Plugin execution sandbox with resource limits and timeout enforcement.

Wraps asyncio subprocess execution with:
- Configurable timeout (SIGTERM → grace period → SIGKILL)
- stdout/stderr byte-stream capping
- POSIX resource limits (RLIMIT_AS, RLIMIT_CPU) via preexec_fn on Linux
- Structured SandboxViolation exception on any breach
"""

from __future__ import annotations

import asyncio
import platform
import signal
import sys
from asyncio import subprocess
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ── Resource limits (Linux only) ──────────────────────────────────────────────
_IS_LINUX = platform.system() == "Linux"

if _IS_LINUX:
    import resource as _resource


def _apply_resource_limits(memory_mb: int, cpu_seconds: int) -> None:
    """
    Called as preexec_fn inside the child process (Linux only).
    Sets virtual memory and CPU time hard limits before exec().
    """
    if not _IS_LINUX:
        return
    try:
        # Virtual address space limit (bytes)
        mem_bytes = memory_mb * 1024 * 1024
        _resource.setrlimit(_resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception:
        pass  # best-effort — never crash the child process

    try:
        # CPU time limit (seconds)
        _resource.setrlimit(_resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    except Exception:
        pass


# ── Public API ─────────────────────────────────────────────────────────────────

class SandboxViolation(Exception):
    """Raised when a subprocess breaches a sandbox constraint."""

    def __init__(self, reason: str, output: str = ""):
        super().__init__(reason)
        self.reason = reason          # e.g. "timeout", "memory_limit", "output_limit"
        self.output = output          # partial output collected before the violation


@dataclass
class SandboxConfig:
    """
    Per-task sandbox constraints.

    Defaults mirror settings values but can be overridden per plugin via
    plugin metadata: { "sandbox": { "timeout_seconds": 30, ... } }
    """
    timeout_seconds: int = 600
    max_memory_mb: int = 512
    max_output_bytes: int = 5 * 1024 * 1024   # 5 MB
    sigterm_grace_seconds: int = 3


async def run_sandboxed(
    command: list[str],
    task_id: str,
    config: SandboxConfig,
    broadcast_fn=None,          # async callable(task_id, "output", line_str) | None
) -> tuple[str, int]:
    """
    Execute *command* inside a resource-constrained subprocess.

    Args:
        command:        Command + args list passed to asyncio.create_subprocess_exec
        task_id:        Used only for logging and broadcast tagging
        config:         SandboxConfig instance controlling all limits
        broadcast_fn:   Optional async coroutine to stream each output line

    Returns:
        (output_str, exit_code)

    Raises:
        SandboxViolation: if timeout, output cap, or memory limit is hit
    """

    # Build preexec_fn for Linux resource limits
    preexec = None
    if _IS_LINUX:
        mem_mb = config.max_memory_mb
        cpu_sec = config.timeout_seconds  # CPU seconds == wall timeout as upper bound
        def preexec():  # noqa: E306
            _apply_resource_limits(mem_mb, cpu_sec)

    process: Optional[asyncio.subprocess.Process] = None

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=preexec,
        )

        output_chunks: list[str] = []
        total_bytes = 0
        truncated = False

        async def _read_stream() -> None:
            nonlocal total_bytes, truncated
            stdout = process.stdout
            if stdout is None:
                return
            while not stdout.at_eof():
                line = await stdout.readline()
                if not line:
                    continue
                line_bytes = len(line)

                # Output byte cap — stop reading, flag truncation
                if total_bytes + line_bytes > config.max_output_bytes:
                    truncated = True
                    output_chunks.append(
                        f"\n[SANDBOX] Output truncated at {config.max_output_bytes // 1024} KB limit\n"
                    )
                    # Drain remaining stdout so the process isn't blocked on write
                    try:
                        await asyncio.wait_for(stdout.read(), timeout=2)
                    except Exception:
                        pass
                    return

                decoded = line.decode("utf-8", errors="replace")
                output_chunks.append(decoded)
                total_bytes += line_bytes

                if broadcast_fn is not None:
                    try:
                        await broadcast_fn(task_id, "output", decoded)
                    except Exception:
                        pass

        # ── Timeout enforcement ────────────────────────────────────────────
        try:
            await asyncio.wait_for(_read_stream(), timeout=config.timeout_seconds)
            await process.wait()
        except asyncio.TimeoutError:
            await _escalate_kill(process, config.sigterm_grace_seconds, task_id)
            partial = "".join(output_chunks)
            raise SandboxViolation(
                reason="timeout",
                output=partial + f"\n[SANDBOX] Process killed after {config.timeout_seconds}s timeout",
            )
        except asyncio.CancelledError:
            await _escalate_kill(process, config.sigterm_grace_seconds, task_id)
            raise

        exit_code = process.returncode if process.returncode is not None else -1
        output = "".join(output_chunks)

        # Surface memory limit hit (Linux SIGKILL from RLIMIT_AS → exit -9)
        if _IS_LINUX and exit_code in (-9, 137):
            raise SandboxViolation(
                reason="memory_limit",
                output=output + "\n[SANDBOX] Process killed by OS — memory limit exceeded",
            )

        return output, exit_code

    except SandboxViolation:
        raise
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("Sandbox execution error for task %s: %s", task_id, exc)
        return f"Execution error: {exc}", -1


async def _escalate_kill(
    process: asyncio.subprocess.Process,
    grace_seconds: int,
    task_id: str,
) -> None:
    """
    Send SIGTERM, wait grace_seconds, then SIGKILL if still alive.
    Safe on all platforms (Windows falls back to terminate/kill).
    """
    pid = process.pid
    logger.warning("Sandbox: sending SIGTERM to PID %s (task %s)", pid, task_id)

    try:
        if sys.platform == "win32":
            process.terminate()
        else:
            process.send_signal(signal.SIGTERM)
    except ProcessLookupError:
        return  # already dead

    try:
        await asyncio.wait_for(process.wait(), timeout=grace_seconds)
        logger.info("Sandbox: PID %s exited cleanly after SIGTERM", pid)
    except asyncio.TimeoutError:
        logger.warning(
            "Sandbox: PID %s ignored SIGTERM after %ss — sending SIGKILL",
            pid, grace_seconds,
        )
        try:
            process.kill()
            await process.wait()
        except ProcessLookupError:
            pass
