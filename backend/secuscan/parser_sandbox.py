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

Security note on stderr
-----------------------
Stderr from the child process may contain stack traces, file paths, partial
parser-input excerpts, or other diagnostic data. It is intentionally NOT
included in the user-facing exception message or stored in ``error_message``.
Full stderr is logged at DEBUG level (internal diagnostics only) so operators
can investigate failures without leaking sensitive details to API callers.
"""

from __future__ import annotations

import json
import os
import re
import sys
import subprocess
import string
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Defaults — overridden by the Settings values passed at call time.
_DEFAULT_TIMEOUT_SECONDS: int = 30
_DEFAULT_MAX_OUTPUT_BYTES: int = 8 * 1024 * 1024  # 8 MB

# Strip absolute file-system paths and Python line-number references from
# stderr before any logging so internal topology is not exposed even in logs
# that might be shipped to external observability platforms.
_PATH_RE = re.compile(r'(?:[A-Za-z]:[\\/]|/)[^\s"\'<>|:*?\n]{3,}')
_LINENO_RE = re.compile(r'\bline \d+\b', re.IGNORECASE)


def _sanitize_stderr(stderr: str, max_chars: int = 500) -> str:
    """Strip file paths and line numbers from stderr; truncate to *max_chars*."""
    sanitized = _PATH_RE.sub("[PATH]", stderr)
    sanitized = _LINENO_RE.sub("[LINE]", sanitized)
    return sanitized[:max_chars]


class ParserSandboxError(RuntimeError):
    """Raised when the sandboxed parser fails for any reason.

    The public exception message intentionally contains only the *reason*
    string (a short, controlled description) and never includes raw stderr
    content.  Stderr is stored privately on the instance so callers that need
    it for internal diagnostics can access it, but it must not be forwarded to
    API responses or stored as a user-facing error message.
    """

    def __init__(self, plugin_id: str, reason: str, stderr: str = "") -> None:
        self.plugin_id = plugin_id
        self.reason = reason
        # Keep stderr private; callers must not surface this to API consumers.
        self._stderr_diagnostic: str = stderr
        # User-facing message: reason only — no stderr content.
        super().__init__(f"Parser sandbox failed for '{plugin_id}' ({reason})")


# ---------------------------------------------------------------------------
# Bootstrap script injected into the child process via -c
# ---------------------------------------------------------------------------
# Uses string.Template (${var} syntax) instead of str.format() so that
# user-controlled values in parser_path (e.g. braces) cannot cause
# KeyError/ValueError via format-string injection.

_BOOTSTRAP_TEMPLATE = string.Template(
    "import sys, json, os\n"
    "\n"
    "# Hard limit: refuse to read more than ${max_input_bytes} bytes from stdin.\n"
    "MAX_INPUT = ${max_input_bytes}\n"
    "raw = sys.stdin.buffer.read(MAX_INPUT + 1)\n"
    "if len(raw) > MAX_INPUT:\n"
    "    sys.stderr.write('Parser input exceeded size limit\\n')\n"
    "    sys.exit(2)\n"
    "\n"
    "try:\n"
    "    envelope = json.loads(raw.decode('utf-8', errors='replace'))\n"
    "    parser_input = envelope['input']\n"
    "except Exception as exc:\n"
    "    sys.stderr.write(f'Failed to decode envelope: {exc}\\n')\n"
    "    sys.exit(3)\n"
    "\n"
    "# Load the plugin's parser module from an absolute path.\n"
    "import importlib.util\n"
    "parser_path = ${parser_path_repr}\n"
    "spec = importlib.util.spec_from_file_location('_plugin_parser', parser_path)\n"
    "if spec is None or spec.loader is None:\n"
    "    sys.stderr.write(f'Cannot load parser\\n')\n"
    "    sys.exit(4)\n"
    "\n"
    "module = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(module)\n"
    "\n"
    "if not hasattr(module, 'parse'):\n"
    "    sys.stderr.write(\"Parser module missing 'parse' function\\n\")\n"
    "    sys.exit(5)\n"
    "\n"
    "result = module.parse(parser_input)\n"
    "\n"
    "# Write result as a single JSON line.\n"
    "sys.stdout.write(json.dumps(result, default=str))\n"
    "sys.stdout.flush()\n"
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

    # Use Template.safe_substitute so that any stray $ in parser_path does not
    # raise; repr() ensures the path is a valid Python string literal.
    bootstrap = _BOOTSTRAP_TEMPLATE.safe_substitute(
        parser_path_repr=repr(str(parser_path)),
        max_input_bytes=max_input_bytes,
    )

    envelope = json.dumps({"input": parser_input})
    stdin_bytes = envelope.encode("utf-8")

    import threading

    stdout_chunks: list[bytes] = []
    stdout_total = 0
    overflow = False
    stderr_chunks: list[bytes] = []
    # Stderr cap: diagnostics only — 64 KB is more than enough for any error message.
    _MAX_STDERR_BYTES = 65536

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
        total = 0
        while True:
            chunk = proc.stderr.read(4096)
            if not chunk:
                break
            total += len(chunk)
            if total <= _MAX_STDERR_BYTES:
                stderr_chunks.append(chunk)
            # Always drain so the child is never blocked on a full pipe.

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
        # Log sanitized stderr for internal diagnostics; do NOT pass to exception.
        logger.debug(
            "Parser sandbox stderr (plugin '%s', timed out): %s",
            plugin_id,
            _sanitize_stderr(stderr_text),
        )
        raise ParserSandboxError(plugin_id, f"timed out after {timeout_seconds}s")

    if proc.returncode != 0:
        logger.error(
            "Parser sandbox exited with code %d for plugin '%s'",
            proc.returncode,
            plugin_id,
        )
        # Log sanitized stderr for internal diagnostics; do NOT pass to exception.
        logger.debug(
            "Parser sandbox stderr (plugin '%s', exit %d): %s",
            plugin_id,
            proc.returncode,
            _sanitize_stderr(stderr_text),
        )
        raise ParserSandboxError(
            plugin_id,
            f"subprocess exited with code {proc.returncode}",
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
        logger.debug(
            "Parser sandbox non-JSON stdout (plugin '%s'): %s",
            plugin_id,
            _sanitize_stderr(stderr_text),
        )
        raise ParserSandboxError(
            plugin_id,
            f"parser returned non-JSON output: {exc}",
        )

    if not isinstance(parsed, (dict, list)):
        raise ParserSandboxError(
            plugin_id,
            f"parser returned unexpected type {type(parsed).__name__}; expected dict or list",
        )
    logger.info("Parser sandbox completed successfully for plugin '%s'", plugin_id)
    return parsed if isinstance(parsed, dict) else {"findings": parsed}
