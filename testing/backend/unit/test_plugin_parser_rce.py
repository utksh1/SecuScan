"""
Security tests for plugin parser RCE prevention (issue #202).

Verifies that:
- verify_parser_at_exec_time() re-checks the digest before exec_module
- A parser.py modified after load-time validation is rejected
- A parser.py with no checksum is allowed (with warning) when enforcement is off
- A parser.py with no checksum is blocked when enforce_parser_integrity is on
- A parser.py where the checksum matches is allowed
- Executor skips exec_module when verify_parser_at_exec_time returns False
- A crashing or timing-out custom parser raises RuntimeError (not silent fallback)
- A sandbox failure never causes fallback to built-in parsers
"""

import hashlib
import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.secuscan.plugins import PluginManager
from backend.secuscan.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_plugin(tmp_path: Path, parser_src: str = "", include_checksum: bool = True):
    """Create a minimal plugin directory with metadata.json and optional parser.py."""
    plugin_dir = tmp_path / "test-rce-plugin"
    plugin_dir.mkdir()

    metadata = {
        "id": "test-rce-plugin",
        "name": "Test RCE Plugin",
        "version": "1.0.0",
        "description": "test",
        "category": "test",
        "engine": {"type": "cli", "binary": "echo"},
        "command_template": ["{target}"],
        "safety": {"level": "safe"},
        "output": {"format": "text", "parser": "custom"},
        "fields": [{"id": "target", "label": "Target", "type": "string"}],
        "presets": {},
    }

    metadata_file = plugin_dir / "metadata.json"

    if parser_src:
        parser_file = plugin_dir / "parser.py"
        parser_file.write_text(parser_src, encoding="utf-8")
    else:
        parser_file = plugin_dir / "parser.py"  # may not exist yet

    if include_checksum:
        # Write metadata without checksum first, compute digest, then add checksum
        metadata_file.write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")
        digest = PluginManager.compute_plugin_digest(metadata_file, parser_file)
        metadata["checksum"] = digest

    metadata_file.write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")
    return plugin_dir, metadata_file


def _make_manager(tmp_path: Path) -> PluginManager:
    return PluginManager(plugins_dir=str(tmp_path))


def _minimal_plugin_meta(checksum: str = None):
    """Return a PluginMetadata-like object for unit tests."""
    from backend.secuscan.models import PluginMetadata
    data = {
        "id": "test-rce-plugin",
        "name": "Test",
        "version": "1.0.0",
        "description": "test",
        "category": "test",
        "engine": {"type": "cli", "binary": "echo"},
        "command_template": [],
        "safety": {"level": "safe"},
        "output": {"format": "text", "parser": "custom"},
        "fields": [],
        "presets": {},
    }
    if checksum:
        data["checksum"] = checksum
    return PluginMetadata(**data)


# ---------------------------------------------------------------------------
# verify_parser_at_exec_time — unit tests
# ---------------------------------------------------------------------------

class TestVerifyParserAtExecTime:
    def test_matching_checksum_returns_true(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "enforce_parser_integrity", True)
        parser_src = "def parse(output): return {'findings': []}\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)

        mgr = _make_manager(tmp_path)
        # Load the checksum from the written metadata
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        plugin = _minimal_plugin_meta(checksum=metadata["checksum"])

        assert mgr.verify_parser_at_exec_time(plugin, plugin_dir) is True

    def test_tampered_parser_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "enforce_parser_integrity", True)
        parser_src = "def parse(output): return {'findings': []}\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)

        # Record checksum with original parser
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        plugin = _minimal_plugin_meta(checksum=metadata["checksum"])

        # Tamper with parser.py after checksum was recorded
        (plugin_dir / "parser.py").write_text(
            "import os; os.system('id')\ndef parse(output): return {'findings': []}\n",
            encoding="utf-8",
        )

        mgr = _make_manager(tmp_path)
        assert mgr.verify_parser_at_exec_time(plugin, plugin_dir) is False

    def test_no_checksum_allowed_when_enforcement_off(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "enforce_parser_integrity", False)
        plugin_dir, _ = _write_plugin(tmp_path, parser_src="", include_checksum=False)
        plugin = _minimal_plugin_meta(checksum=None)

        mgr = _make_manager(tmp_path)
        assert mgr.verify_parser_at_exec_time(plugin, plugin_dir) is True

    def test_no_checksum_blocked_when_enforcement_on(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "enforce_parser_integrity", True)
        plugin_dir, _ = _write_plugin(tmp_path, parser_src="", include_checksum=False)
        plugin = _minimal_plugin_meta(checksum=None)

        mgr = _make_manager(tmp_path)
        assert mgr.verify_parser_at_exec_time(plugin, plugin_dir) is False

    def test_digest_compute_failure_returns_false(self, tmp_path, monkeypatch):
        """If the digest computation raises (e.g. permissions), reject execution."""
        monkeypatch.setattr(settings, "enforce_parser_integrity", True)
        plugin_dir, _ = _write_plugin(tmp_path, parser_src="", include_checksum=True)
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        plugin = _minimal_plugin_meta(checksum=metadata.get("checksum", "abc"))

        mgr = _make_manager(tmp_path)
        with patch.object(
            PluginManager, "compute_plugin_digest", side_effect=OSError("permission denied")
        ):
            assert mgr.verify_parser_at_exec_time(plugin, plugin_dir) is False


# ---------------------------------------------------------------------------
# Executor integration — exec_module is NOT called when check fails
# ---------------------------------------------------------------------------

class TestExecutorParserGate:
    def test_integrity_failure_raises_and_blocks_exec(self, tmp_path, monkeypatch):
        """When verify_parser_at_exec_time returns False the task must fail with a security error."""
        monkeypatch.setattr(settings, "enforce_parser_integrity", False)

        parser_src = "def parse(output): return {'findings': []}\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)
        metadata = json.loads((plugin_dir / "metadata.json").read_text())

        # Tamper with parser.py so the digest no longer matches
        (plugin_dir / "parser.py").write_text(
            "import sys; sys.exit(99)\ndef parse(output): return {}\n",
            encoding="utf-8",
        )

        plugin = _minimal_plugin_meta(checksum=metadata["checksum"])

        mgr = _make_manager(tmp_path)
        mgr.plugins_dir = tmp_path
        mgr.plugins[plugin.id] = plugin

        exec_called = []

        with patch("importlib.util.spec_from_file_location") as mock_spec:
            mock_loader = MagicMock()
            mock_loader.exec_module = MagicMock(side_effect=lambda m: exec_called.append(True))
            mock_spec_obj = MagicMock()
            mock_spec_obj.loader = mock_loader
            mock_spec.return_value = mock_spec_obj

            with patch("importlib.util.module_from_spec", return_value=MagicMock()):
                from backend.secuscan import executor as executor_module

                exec_instance = executor_module.TaskExecutor.__new__(executor_module.TaskExecutor)

                with patch(
                    "backend.secuscan.executor.get_plugin_manager", return_value=mgr
                ):
                    with pytest.raises(ValueError, match="Security error.*integrity check failed"):
                        exec_instance._parse_results(plugin, "raw output")

        assert len(exec_called) == 0, "exec_module must not be called when integrity check fails"

    def test_sandbox_called_when_integrity_passes(self, tmp_path, monkeypatch):
        """When verify_parser_at_exec_time returns True, run_parser_in_sandbox must be called."""
        monkeypatch.setattr(settings, "enforce_parser_integrity", False)

        parser_src = "def parse(output):\n    return {'findings': []}\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        plugin = _minimal_plugin_meta(checksum=metadata["checksum"])

        mgr = _make_manager(tmp_path)
        mgr.plugins_dir = tmp_path
        mgr.plugins[plugin.id] = plugin

        sandbox_called = []

        def _fake_sandbox(parser_path, plugin_id, parser_input, **kwargs):
            sandbox_called.append(plugin_id)
            return {"findings": []}

        from backend.secuscan import executor as executor_module
        exec_instance = executor_module.TaskExecutor.__new__(executor_module.TaskExecutor)

        with patch("backend.secuscan.executor.get_plugin_manager", return_value=mgr), \
             patch("backend.secuscan.executor.run_parser_in_sandbox", side_effect=_fake_sandbox):
            result = exec_instance._parse_results(plugin, "raw output")

        assert len(sandbox_called) == 1, "run_parser_in_sandbox must be called once when integrity check passes"
        assert sandbox_called[0] == plugin.id


# ---------------------------------------------------------------------------
# Sandbox failure must not silently fall back to built-in parsers
# ---------------------------------------------------------------------------


class TestSandboxFailureIsHardError:
    """Regression: a crashing or timing-out custom parser must fail the task,
    not silently fall through to the built-in nmap/http/empty parser path."""

    def _make_exec_instance(self, tmp_path, plugin):
        from backend.secuscan import executor as executor_module
        mgr = _make_manager(tmp_path)
        mgr.plugins_dir = tmp_path
        mgr.plugins[plugin.id] = plugin
        exec_instance = executor_module.TaskExecutor.__new__(executor_module.TaskExecutor)
        return exec_instance, mgr

    def test_sandbox_crash_raises_runtime_error(self, tmp_path, monkeypatch):
        """ParserSandboxError from a crashing parser must surface as RuntimeError."""
        monkeypatch.setattr(settings, "enforce_parser_integrity", False)

        parser_src = "def parse(output): raise RuntimeError('boom')\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        plugin = _minimal_plugin_meta(checksum=metadata["checksum"])

        exec_instance, mgr = self._make_exec_instance(tmp_path, plugin)

        with patch("backend.secuscan.executor.get_plugin_manager", return_value=mgr):
            with pytest.raises(RuntimeError, match="Custom parser failed"):
                exec_instance._parse_results(plugin, "raw output")

    def test_sandbox_timeout_raises_runtime_error(self, tmp_path, monkeypatch):
        """ParserSandboxError from a timing-out parser must surface as RuntimeError."""
        from backend.secuscan.parser_sandbox import ParserSandboxError
        monkeypatch.setattr(settings, "enforce_parser_integrity", False)

        parser_src = "def parse(output): return {}\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        plugin = _minimal_plugin_meta(checksum=metadata["checksum"])

        exec_instance, mgr = self._make_exec_instance(tmp_path, plugin)

        def _timeout_sandbox(**kwargs):
            raise ParserSandboxError(plugin.id, "timed out after 1s")

        with patch("backend.secuscan.executor.get_plugin_manager", return_value=mgr), \
             patch("backend.secuscan.executor.run_parser_in_sandbox", side_effect=_timeout_sandbox):
            with pytest.raises(RuntimeError, match="Custom parser failed"):
                exec_instance._parse_results(plugin, "raw output")

    def test_sandbox_failure_does_not_call_builtin_nmap_parser(self, tmp_path, monkeypatch):
        """Regression: built-in nmap parser must NOT be invoked after sandbox failure."""
        from backend.secuscan.parser_sandbox import ParserSandboxError
        monkeypatch.setattr(settings, "enforce_parser_integrity", False)

        parser_src = "def parse(output): return {}\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)
        metadata = json.loads((plugin_dir / "metadata.json").read_text())

        # Give the plugin parser_type = builtin_nmap so the fallback path would
        # normally produce nmap-structured output — proving it is never reached.
        from backend.secuscan.models import PluginMetadata
        plugin_data = {
            "id": "test-rce-plugin",
            "name": "Test",
            "version": "1.0.0",
            "description": "test",
            "category": "test",
            "engine": {"type": "cli", "binary": "nmap"},
            "command_template": [],
            "safety": {"level": "safe"},
            "output": {"format": "text", "parser": "builtin_nmap"},
            "fields": [],
            "presets": {},
            "checksum": metadata["checksum"],
        }
        plugin = PluginMetadata(**plugin_data)

        exec_instance, mgr = self._make_exec_instance(tmp_path, plugin)
        nmap_called = []

        def _crash_sandbox(**kwargs):
            raise ParserSandboxError(plugin.id, "subprocess exited with code 1")

        from backend.secuscan import executor as executor_module
        with patch("backend.secuscan.executor.get_plugin_manager", return_value=mgr), \
             patch("backend.secuscan.executor.run_parser_in_sandbox", side_effect=_crash_sandbox), \
             patch.object(executor_module.TaskExecutor, "_parse_nmap_output",
                          side_effect=lambda s: nmap_called.append(True) or {}):
            with pytest.raises(RuntimeError):
                exec_instance._parse_results(plugin, "raw output")

        assert len(nmap_called) == 0, (
            "_parse_nmap_output must never be called after sandbox failure"
        )
