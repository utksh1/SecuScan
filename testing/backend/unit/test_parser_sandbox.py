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
