"""
Sandboxed parser execution for custom plugin parser.py files.

Plugin parsers run untrusted third-party code.  This module executes each
parser in a fresh, short-lived subprocess so that:

  - A crash, infinite loop, or memory explosion in the parser cannot kill the
    backend process.
  - The parser cannot access the backend's secrets, database handles, or any
    other in-process state.
  - Environment variables (which may contain SECUSCAN_VAULT_KEY, API keys, etc.)
    are stripped from the child process.
  - Execution is bounded by a configurable timeout.
  - Output size is capped so a runaway parser cannot exhaust backend memory.

Communication contract
----------------------
  stdin  → JSON line: {"input": <parser_input_string>}
  stdout → JSON line: <parsed_result_dict>
  stderr → captured for diagnostics only

The child process is a minimal Python bootstrap that imports the plugin's
parser.py, calls parse(input_data), and writes the result to stdout.  It
imports nothing from the backend package, so no application state leaks.
"""

from __future__ import annotations

import json
import os
import sys
import subprocess
import textwrap
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Defaults — overridden by the Settings values passed at call time.
_DEFAULT_TIMEOUT_SECONDS: int = 30
_DEFAULT_MAX_OUTPUT_BYTES: int = 8 * 1024 * 1024  # 8 MB


class ParserSandboxError(RuntimeError):
    """Raised when the sandboxed parser fails for any reason."""

    def __init__(self, plugin_id: str, reason: str, stderr: str = "") -> None:
        self.plugin_id = plugin_id
        self.reason = reason
        self.stderr_excerpt = stderr[:2000] if stderr else ""
        detail = f": {stderr[:200]}" if stderr.strip() else ""
        super().__init__(f"Parser sandbox failed for '{plugin_id}' ({reason}){detail}")


# ---------------------------------------------------------------------------
# Bootstrap script injected into the child process via -c
# ---------------------------------------------------------------------------

_BOOTSTRAP_TEMPLATE = textwrap.dedent(
    """\
    import sys, json, os

    # Hard limit: refuse to read more than {max_input_bytes} bytes from stdin.
    MAX_INPUT = {max_input_bytes}
    raw = sys.stdin.buffer.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        sys.stderr.write("Parser input exceeded size limit\\n")
        sys.exit(2)

    try:
        envelope = json.loads(raw.decode("utf-8", errors="replace"))
        parser_input = envelope["input"]
    except Exception as exc:
        sys.stderr.write(f"Failed to decode envelope: {{exc}}\\n")
        sys.exit(3)

    # Load the plugin's parser module from an absolute path.
    import importlib.util
    parser_path = {parser_path!r}
    spec = importlib.util.spec_from_file_location("_plugin_parser", parser_path)
    if spec is None or spec.loader is None:
        sys.stderr.write(f"Cannot load parser from {{parser_path}}\\n")
        sys.exit(4)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "parse"):
        sys.stderr.write("Parser module missing 'parse' function\\n")
        sys.exit(5)

    result = module.parse(parser_input)

    # Write result as a single JSON line.
    sys.stdout.write(json.dumps(result, default=str))
    sys.stdout.flush()
"""
)


def _sanitised_env() -> Dict[str, str]:
    """Return a minimal environment for the child process.

    Retains PATH and PYTHONPATH (needed to locate the interpreter and any
    installed packages) while stripping all credentials and application
    secrets present in the parent's environment.
    """
    keep_keys = {"PATH", "PYTHONPATH", "HOME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL"}
    return {k: v for k, v in os.environ.items() if k in keep_keys}


def run_parser_in_sandbox(
    parser_path: Path,
    plugin_id: str,
    parser_input: str,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
    max_output_bytes: int = _DEFAULT_MAX_OUTPUT_BYTES,
) -> Dict[str, Any]:
    """Execute plugin parser.py in an isolated subprocess and return its result.

    Args:
        parser_path:     Absolute path to the plugin's parser.py.
        plugin_id:       Plugin identifier used in log and error messages.
        parser_input:    The raw string output from the scanner to parse.
        timeout_seconds: Hard wall-clock timeout; the child is killed when exceeded.
        max_output_bytes: Maximum bytes accepted from the child's stdout.

    Returns:
        The dict returned by the parser's ``parse()`` function.

    Raises:
        ParserSandboxError: on timeout, crash, oversized output, or malformed JSON.
    """
    if not parser_path.exists():
        raise ParserSandboxError(plugin_id, "parser.py not found")

    max_input_bytes = max(len(parser_input.encode("utf-8")) + 128, 64 * 1024)

    bootstrap = _BOOTSTRAP_TEMPLATE.format(
        parser_path=str(parser_path),
        max_input_bytes=max_input_bytes,
    )

    envelope = json.dumps({"input": parser_input})
    stdin_bytes = envelope.encode("utf-8")

    import threading
    import time

    stdout_chunks: list[bytes] = []
    stdout_total = 0
    overflow = False
    stderr_chunks: list[bytes] = []

    proc = subprocess.Popen(
        [sys.executable, "-c", bootstrap],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_sanitised_env(),
    )

    def _read_stdout() -> None:
        nonlocal stdout_total, overflow
        assert proc.stdout is not None
        while True:
            chunk = proc.stdout.read(65536)
            if not chunk:
                break
            stdout_total += len(chunk)
            if stdout_total > max_output_bytes:
                overflow = True
                proc.kill()
                break
            stdout_chunks.append(chunk)

    def _read_stderr() -> None:
        assert proc.stderr is not None
        while True:
            chunk = proc.stderr.read(4096)
            if not chunk:
                break
            stderr_chunks.append(chunk)

    t_out = threading.Thread(target=_read_stdout, daemon=True)
    t_err = threading.Thread(target=_read_stderr, daemon=True)
    t_out.start()
    t_err.start()

    try:
        proc.stdin.write(stdin_bytes)  # type: ignore[union-attr]
        proc.stdin.close()  # type: ignore[union-attr]
    except BrokenPipeError:
        pass

    timed_out = False
    try:
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()

    t_out.join(timeout=5)
    t_err.join(timeout=5)

    stderr_text = b"".join(stderr_chunks).decode("utf-8", errors="replace")

    if overflow:
        raise ParserSandboxError(
            plugin_id,
            f"output exceeded {max_output_bytes // (1024 * 1024)} MB limit",
        )

    if timed_out:
        logger.warning(
            "Parser sandbox timed out after %ds for plugin '%s'",
            timeout_seconds,
            plugin_id,
        )
        raise ParserSandboxError(plugin_id, f"timed out after {timeout_seconds}s", stderr_text)

    if proc.returncode != 0:
        logger.error(
            "Parser sandbox exited with code %d for plugin '%s': %s",
            proc.returncode,
            plugin_id,
            stderr_text[:500],
        )
        raise ParserSandboxError(
            plugin_id,
            f"subprocess exited with code {proc.returncode}",
            stderr_text,
        )

    stdout_bytes = b"".join(stdout_chunks)

    if not stdout_bytes.strip():
        logger.warning(
            "Parser sandbox produced no output for plugin '%s'; treating as empty result",
            plugin_id,
        )
        return {}

    try:
        parsed = json.loads(stdout_bytes.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise ParserSandboxError(
            plugin_id,
            f"parser returned non-JSON output: {exc}",
            stderr_text,
        )

    if not isinstance(parsed, (dict, list)):
        raise ParserSandboxError(
            plugin_id,
            f"parser returned unexpected type {type(parsed).__name__}; expected dict or list",
        )

    logger.info("Parser sandbox completed successfully for plugin '%s'", plugin_id)
    return parsed if isinstance(parsed, dict) else {"findings": parsed}
