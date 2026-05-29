import asyncio
import logging
import platform
from asyncio import subprocess
from typing import List, Optional, Tuple

from .models import SandboxConfig

logger = logging.getLogger(__name__)

IS_LINUX = platform.system() == "Linux"

CHUNK_SIZE = 64 * 1024
SIGTERM_GRACE = 3.0


def resolve_sandbox_config(plugin_sandbox: Optional[SandboxConfig] = None) -> SandboxConfig:
    """Merge global settings with optional per-plugin sandbox overrides."""
    from .config import settings
    base = SandboxConfig(
        timeout_seconds=settings.sandbox_timeout,
        max_memory_mb=settings.sandbox_memory_mb,
        max_output_bytes=settings.sandbox_max_output_bytes,
        allow_network=settings.sandbox_allow_network,
    )
    if not plugin_sandbox:
        return base
    overrides = plugin_sandbox.model_dump(exclude_none=True)
    return base.model_copy(update=overrides)


def _build_preexec_fn(config: SandboxConfig):
    """Build preexec_fn for Linux that applies RLIMIT_AS."""
    mem_limit = config.max_memory_mb * 1024 * 1024

    def _apply_limits():
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))

    return _apply_limits


def classify_memory_violation(
    exit_code: int,
    stderr_text: str,
    rss_bytes: int,
    limit_bytes: int,
) -> bool:
    """Post-mortem heuristic to classify whether failure was caused by memory exhaustion."""
    if exit_code in (-11, 139):
        return True
    if "MemoryError" in stderr_text or "Cannot allocate memory" in stderr_text:
        return True
    if rss_bytes >= limit_bytes * 95 // 100 and exit_code != 0:
        return True
    return False


async def _terminate_process(process):
    """Graceful SIGTERM -> 3s grace -> SIGKILL escalation. Always reaps."""
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=SIGTERM_GRACE)
    except asyncio.TimeoutError:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        await process.wait()


async def _read_stream(stream, buffer, state):
    """Read from a stream in 64KB chunks, respecting max_output_bytes limit."""
    while True:
        chunk = await stream.read(CHUNK_SIZE)
        if not chunk:
            break
        if state["limit_hit"]:
            break
        remaining = state["max_bytes"] - state["total_bytes"]
        if remaining <= 0:
            state["limit_hit"] = True
            break
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
            state["limit_hit"] = True
        buffer.extend(chunk)
        state["total_bytes"] += len(chunk)


async def sandbox_execute(
    cmd: List[str],
    config: SandboxConfig,
) -> Tuple[str, str, int, Optional[str]]:
    """
    Execute a subprocess under sandbox resource constraints.

    Returns (stdout_str, stderr_str, exit_code, violation_reason).
    violation_reason is None on success, or one of
    "timeout", "memory_limit", "output_limit".
    """
    preexec_fn = _build_preexec_fn(config) if IS_LINUX else None

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=preexec_fn,
    )

    stdout_buffer = bytearray()
    stderr_buffer = bytearray()

    state = {
        "total_bytes": 0,
        "max_bytes": config.max_output_bytes,
        "limit_hit": False,
    }

    violation_reason = None

    reader_task = asyncio.gather(
        _read_stream(process.stdout, stdout_buffer, state),
        _read_stream(process.stderr, stderr_buffer, state),
    )

    try:
        try:
            await asyncio.wait_for(reader_task, timeout=config.timeout_seconds)
        except asyncio.TimeoutError:
            if state["limit_hit"]:
                violation_reason = "output_limit"
            else:
                violation_reason = "timeout"
            reader_task.cancel()
            try:
                await reader_task
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            await _terminate_process(process)
        else:
            if state["limit_hit"]:
                violation_reason = "output_limit"
                await _terminate_process(process)
            else:
                await process.wait()
    except asyncio.CancelledError:
        violation_reason = None
        if not reader_task.done():
            reader_task.cancel()
            try:
                await reader_task
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        raise
    finally:
        if process.returncode is None:
            await _terminate_process(process)

    stdout_str = stdout_buffer.decode("utf-8", errors="replace")
    stderr_str = stderr_buffer.decode("utf-8", errors="replace")
    exit_code = process.returncode if process.returncode is not None else -1

    if violation_reason is None and exit_code != 0:
        rss_bytes = 0
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_CHILDREN)
            if IS_LINUX:
                rss_bytes = usage.ru_maxrss * 1024
            else:
                rss_bytes = usage.ru_maxrss
        except (ImportError, AttributeError):
            pass

        limit_bytes = config.max_memory_mb * 1024 * 1024

        if classify_memory_violation(exit_code, stderr_str, rss_bytes, limit_bytes):
            violation_reason = "memory_limit"

    return stdout_str, stderr_str, exit_code, violation_reason
