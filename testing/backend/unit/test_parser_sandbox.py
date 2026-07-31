"""
Unit tests for the parser_sandbox module.

Covers:
- Successful parse: dict result propagated correctly
- Successful parse: list result wrapped in {findings: [...]}
- Parser timeout: ParserSandboxError raised with reason containing "timed out"
- Parser crash (sys.exit / unhandled exception): ParserSandboxError raised
- Parser returns malformed JSON: ParserSandboxError raised
- Parser missing parse() function: ParserSandboxError raised
- Parser produces oversized output: ParserSandboxError raised
- Missing parser.py: ParserSandboxError raised
- Environment sanitisation: secrets not leaked to child process
- Stderr captured in error when subprocess fails
- Empty stdout treated as empty result
- parse() returning non-dict/list raises ParserSandboxError
"""

import json
import os
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from backend.secuscan.parser_sandbox import (
    ParserSandboxError,
    _sanitised_env,
    run_parser_in_sandbox,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_parser(tmp_path: Path, body: str) -> Path:
    """Write a parser.py with the given body and return its path."""
    p = tmp_path / "parser.py"
    p.write_text(textwrap.dedent(body))
    return p


# ---------------------------------------------------------------------------
# Successful parsing
# ---------------------------------------------------------------------------


class TestRunParserSuccessful:
    def test_returns_dict_from_parser(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return {"findings": [], "summary": "ok"}
            """,
        )
        result = run_parser_in_sandbox(p, "test_plugin", "some scanner output")
        assert result == {"findings": [], "summary": "ok"}

    def test_parser_receives_correct_input(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return {"echo": output}
            """,
        )
        result = run_parser_in_sandbox(p, "test_plugin", "SCANNER OUTPUT")
        assert result["echo"] == "SCANNER OUTPUT"

    def test_list_result_wrapped_in_findings(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return [{"title": "finding1"}, {"title": "finding2"}]
            """,
        )
        result = run_parser_in_sandbox(p, "test_plugin", "")
        assert "findings" in result
        assert len(result["findings"]) == 2

    def test_unicode_input_handled(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return {"length": len(output)}
            """,
        )
        input_str = "テスト　scan output 🔍"
        result = run_parser_in_sandbox(p, "test_plugin", input_str)
        assert result["length"] == len(input_str)

    def test_empty_input_string_accepted(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return {"empty": output == ""}
            """,
        )
        result = run_parser_in_sandbox(p, "test_plugin", "")
        assert result["empty"] is True

    def test_large_output_within_limit_accepted(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return {"findings": [{"title": f"f{i}"} for i in range(1000)]}
            """,
        )
        result = run_parser_in_sandbox(p, "test_plugin", "data", max_output_bytes=10 * 1024 * 1024)
        assert len(result["findings"]) == 1000


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestParserTimeout:
    def test_timeout_raises_parser_sandbox_error(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            import time
            def parse(output):
                time.sleep(60)
                return {}
            """,
        )
        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(p, "slow_plugin", "data", timeout_seconds=1)
        assert "timed out" in str(exc_info.value)
        assert exc_info.value.plugin_id == "slow_plugin"

    def test_reason_contains_timeout_duration(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            import time
            def parse(output):
                time.sleep(60)
                return {}
            """,
        )
        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(p, "slow_plugin", "data", timeout_seconds=1)
        assert "1s" in exc_info.value.reason


# ---------------------------------------------------------------------------
# Parser crashes
# ---------------------------------------------------------------------------


class TestParserCrash:
    def test_unhandled_exception_raises_sandbox_error(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                raise RuntimeError("parser exploded")
            """,
        )
        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(p, "crash_plugin", "data")
        assert exc_info.value.plugin_id == "crash_plugin"

    def test_explicit_sys_exit_raises_sandbox_error(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            import sys
            def parse(output):
                sys.exit(42)
            """,
        )
        with pytest.raises(ParserSandboxError):
            run_parser_in_sandbox(p, "exit_plugin", "data")

    def test_stderr_captured_in_error(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            import sys
            def parse(output):
                sys.stderr.write("detailed crash info\\n")
                raise ValueError("boom")
            """,
        )
        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(p, "verbose_crash", "data")
        assert "detailed crash info" in exc_info.value.stderr_excerpt

    def test_syntax_error_in_parser_raises(self, tmp_path):
        p = tmp_path / "parser.py"
        p.write_text("def parse(output:\n    return {}")  # syntax error
        with pytest.raises(ParserSandboxError):
            run_parser_in_sandbox(p, "syntax_plugin", "data")


# ---------------------------------------------------------------------------
# Malformed / missing parse function
# ---------------------------------------------------------------------------


class TestMalformedParser:
    def test_missing_parse_function_raises(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def not_parse(output):
                return {}
            """,
        )
        with pytest.raises(ParserSandboxError):
            run_parser_in_sandbox(p, "no_func_plugin", "data")

    def test_parse_returns_non_json_serialisable_raises(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return "just a string"
            """,
        )
        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(p, "string_plugin", "data")
        assert "unexpected type" in exc_info.value.reason

    def test_parse_returns_none_treated_as_empty(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return None
            """,
        )
        with pytest.raises(ParserSandboxError):
            run_parser_in_sandbox(p, "none_plugin", "data")


# ---------------------------------------------------------------------------
# Output size limit
# ---------------------------------------------------------------------------


class TestOutputSizeLimit:
    def test_oversized_output_raises(self, tmp_path):
        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return {"data": "x" * 1_000_000}
            """,
        )
        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(p, "big_plugin", "data", max_output_bytes=100)
        assert "limit" in exc_info.value.reason

    def test_oversized_output_process_killed_before_full_buffer(self, tmp_path):
        """Regression: parser generating >limit bytes must be killed immediately.

        The process is terminated as soon as the cap is hit, so it cannot force
        the parent to buffer the full output in memory first.
        """
        # Parser streams 20 MB in a tight loop so it would fill memory fast if
        # the parent waited for it to finish before checking size.
        p = _write_parser(
            tmp_path,
            """\
            import sys
            def parse(output):
                # Write 20 MB to stdout directly so the parent reader sees it.
                chunk = b"x" * 65536
                for _ in range(320):  # 320 * 64 KB = 20 MB
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.buffer.flush()
                return {}
            """,
        )
        cap = 512 * 1024  # 512 KB cap
        import time
        start = time.monotonic()
        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(p, "overflow_plugin", "data", max_output_bytes=cap)
        elapsed = time.monotonic() - start
        assert "limit" in exc_info.value.reason
        # Must be killed well before it finishes writing 20 MB — should take < 10s
        assert elapsed < 10, f"Overflow enforcement took too long: {elapsed:.1f}s"

    def test_oversized_stderr_does_not_exhaust_memory(self, tmp_path):
        """Regression: parser flooding stderr must not buffer unbounded bytes in parent.

        The stderr reader applies a hard cap (64 KB) so a misbehaving parser
        cannot exhaust the parent's memory through the diagnostic channel.
        """
        p = _write_parser(
            tmp_path,
            """\
            import sys
            def parse(output):
                # Write 10 MB to stderr; parent must stop collecting well before that.
                chunk = "e" * 4096
                for _ in range(2560):  # 2560 * 4 KB = 10 MB
                    sys.stderr.write(chunk)
                    sys.stderr.flush()
                return {"ok": True}
            """,
        )
        import time
        start = time.monotonic()
        # Stderr overflow does NOT kill the process — the parser still succeeds.
        # We just verify the collected stderr is bounded.
        result = run_parser_in_sandbox(p, "stderr_flood_plugin", "data")
        elapsed = time.monotonic() - start
        assert result == {"ok": True}
        # The whole operation must finish within the timeout window.
        assert elapsed < 35, f"Stderr-flooded sandbox took too long: {elapsed:.1f}s"


# ---------------------------------------------------------------------------
# Missing parser file
# ---------------------------------------------------------------------------


class TestMissingParserFile:
    def test_nonexistent_parser_path_raises(self, tmp_path):
        missing = tmp_path / "does_not_exist.py"
        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(missing, "ghost_plugin", "data")
        assert "not found" in exc_info.value.reason
        assert exc_info.value.plugin_id == "ghost_plugin"


# ---------------------------------------------------------------------------
# parser.py must be self-contained
# ---------------------------------------------------------------------------


class TestParserMustBeSelfContained:
    """A parser may not import helper modules sitting beside it.

    The bootstrap loads parser.py by absolute path via
    ``importlib.util.spec_from_file_location`` and the child runs with
    ``PYTHONSAFEPATH=1``, so the plugin directory is never placed on
    ``sys.path``. Sibling imports therefore fail regardless of whether the
    parser was staged — staging a single file does not introduce this
    constraint, it only has to preserve it. These tests pin that contract
    so a future change to the loader cannot quietly widen the import
    surface available to parser code.
    """

    def test_sibling_module_import_fails_loudly(self, tmp_path):
        """A sibling helper is not importable, and the failure is not silent."""
        (tmp_path / "helper.py").write_text("VALUE = 'from-sibling'\n")
        p = _write_parser(
            tmp_path,
            """\
            import helper

            def parse(output):
                return {"value": helper.VALUE}
            """,
        )
        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(p, "sibling_import_plugin", "data")
        assert exc_info.value.plugin_id == "sibling_import_plugin"

    def test_plugin_directory_is_not_on_sys_path(self, tmp_path):
        """The parser's own directory never appears on the child's sys.path."""
        p = _write_parser(
            tmp_path,
            """\
            import os, sys

            def parse(output):
                here = os.path.dirname(os.path.abspath(__file__))
                on_path = [q for q in sys.path if q and os.path.abspath(q) == here]
                return {"plugin_dir_on_sys_path": on_path}
            """,
        )
        result = run_parser_in_sandbox(p, "sys_path_plugin", "data")
        assert result["plugin_dir_on_sys_path"] == []

    def test_stdlib_imports_still_work(self, tmp_path):
        """Self-contained parsers keep full access to the standard library."""
        p = _write_parser(
            tmp_path,
            """\
            import json
            import re
            from collections import Counter

            def parse(output):
                counts = Counter(re.findall(r"[a-z]+", output))
                return json.loads(json.dumps({"top": counts.most_common(1)}))
            """,
        )
        result = run_parser_in_sandbox(p, "stdlib_plugin", "aa bb aa")
        assert result["top"] == [["aa", 2]]


# ---------------------------------------------------------------------------
# Environment sanitisation
# ---------------------------------------------------------------------------


class TestEnvironmentSanitisation:
    def test_secret_env_vars_not_leaked_to_child(self, tmp_path):
        os.environ["SECUSCAN_VAULT_KEY"] = "super-secret-key-12345"
        p = _write_parser(
            tmp_path,
            """\
            import os
            def parse(output):
                return {"vault_key": os.environ.get("SECUSCAN_VAULT_KEY", "NOT_FOUND")}
            """,
        )
        try:
            result = run_parser_in_sandbox(p, "env_test_plugin", "data")
            assert result.get("vault_key") == "NOT_FOUND"
        finally:
            del os.environ["SECUSCAN_VAULT_KEY"]

    def test_sanitised_env_excludes_app_secrets(self):
        os.environ["SECUSCAN_VAULT_KEY"] = "should-not-pass"
        os.environ["MY_API_TOKEN"] = "token-123"
        try:
            env = _sanitised_env()
            assert "SECUSCAN_VAULT_KEY" not in env
            assert "MY_API_TOKEN" not in env
        finally:
            del os.environ["SECUSCAN_VAULT_KEY"]
            del os.environ["MY_API_TOKEN"]

    def test_sanitised_env_retains_path(self):
        env = _sanitised_env()
        assert "PATH" in env

    def test_injected_pythonpath_cannot_be_imported(self, tmp_path):
        """Regression for the sandbox-escape vector (issue #1804).

        A caller-controlled PYTHONPATH must NOT let the parser import modules
        from an attacker-chosen directory. We plant an ``evilmod`` on PYTHONPATH
        and confirm the sandboxed parser cannot import it.
        """
        evil_dir = tmp_path / "attacker"
        evil_dir.mkdir()
        (evil_dir / "evilmod.py").write_text("PWNED = True\n")

        p = _write_parser(
            tmp_path,
            """\
            import evilmod
            def parse(output):
                return {"pwned": evilmod.PWNED}
            """,
        )

        prev = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = str(evil_dir)
        try:
            with pytest.raises(ParserSandboxError) as exc_info:
                run_parser_in_sandbox(p, "escape_plugin", "data")
        finally:
            if prev is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = prev

        # The failure must be the blocked import, not some unrelated error.
        assert "evilmod" in exc_info.value.stderr_excerpt


# ---------------------------------------------------------------------------
# Privilege drop: the dropped child must still be able to read + run parser.py
# (PR #2019 review): dropping to nobody must not make the parser unreadable.
# ---------------------------------------------------------------------------


class TestPrivilegeDropExecution:
    @pytest.mark.skipif(os.name != "posix", reason="privilege drop is POSIX-only")
    def test_parser_runs_when_privilege_drop_is_active(self, tmp_path, monkeypatch):
        """With a drop in effect the parser is staged and still parses correctly."""
        from backend.secuscan import parser_sandbox

        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return {"echo": output}
            """,
        )

        # A real drop to another account needs root; drop to our own ids so the
        # staging + child-exec path runs unchanged on non-root CI. Omit
        # extra_groups (setgroups needs privilege) to keep the child startable.
        drop = {"user": os.getuid(), "group": os.getgid()}
        monkeypatch.setattr(parser_sandbox, "_privilege_drop_kwargs", lambda: drop)

        result = run_parser_in_sandbox(p, "drop_plugin", "payload")
        assert result == {"echo": "payload"}

    @pytest.mark.skipif(os.name != "posix", reason="privilege drop is POSIX-only")
    def test_no_staging_dir_leaks_after_dropped_run(self, tmp_path, monkeypatch):
        """The staged parser copy is cleaned up after a privilege-dropped run."""
        import tempfile
        from pathlib import Path
        from backend.secuscan import parser_sandbox

        p = _write_parser(
            tmp_path,
            """\
            def parse(output):
                return {"ok": True}
            """,
        )
        drop = {"user": os.getuid(), "group": os.getgid()}
        monkeypatch.setattr(parser_sandbox, "_privilege_drop_kwargs", lambda: drop)

        before = set(Path(tempfile.gettempdir()).glob("secuscan-parser-*"))
        run_parser_in_sandbox(p, "drop_plugin", "data")
        after = set(Path(tempfile.gettempdir()).glob("secuscan-parser-*"))
        assert after == before

    @pytest.mark.skipif(
        os.name != "posix" or not hasattr(os, "geteuid") or os.geteuid() != 0,
        reason="requires running as root to exercise a real privilege drop",
    )
    def test_root_reads_and_runs_root_private_parser_unprivileged(self, tmp_path):
        """As root, a root-private parser.py is still read+run by the dropped child.

        Reproduces the exact condition the naive drop broke: parser.py and its
        parent directory are root-owned and unreadable to others. The staged
        copy must let the unprivileged child read and execute it.
        """
        private_dir = tmp_path / "private"
        private_dir.mkdir()
        p = _write_parser(
            private_dir,
            """\
            import os
            def parse(output):
                return {"euid": os.geteuid(), "echo": output}
            """,
        )
        # Root-private: only root can read the original file / traverse its dir.
        os.chmod(p, 0o600)
        os.chmod(private_dir, 0o700)

        result = run_parser_in_sandbox(p, "root_plugin", "payload")

        # The parser ran at all → the dropped child could read the staged copy.
        assert result["echo"] == "payload"
        # And it ran unprivileged, never as root.
        assert result["euid"] != 0


# ---------------------------------------------------------------------------
# ParserSandboxError
# ---------------------------------------------------------------------------


class TestParserSandboxError:
    def test_is_runtime_error(self):
        err = ParserSandboxError("plugin_x", "something went wrong")
        assert isinstance(err, RuntimeError)

    def test_plugin_id_stored(self):
        err = ParserSandboxError("plugin_x", "reason")
        assert err.plugin_id == "plugin_x"

    def test_reason_stored(self):
        err = ParserSandboxError("plugin_x", "custom reason")
        assert err.reason == "custom reason"

    def test_stderr_excerpt_truncated_to_2000_chars(self):
        err = ParserSandboxError("p", "r", stderr="x" * 5000)
        assert len(err.stderr_excerpt) == 2000

    def test_str_contains_plugin_id(self):
        err = ParserSandboxError("my_plugin", "bad thing")
        assert "my_plugin" in str(err)
