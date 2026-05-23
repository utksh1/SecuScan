"""
Security tests for plugin parser RCE prevention (issue #202).

Verifies that:
- verify_parser_at_exec_time() re-checks the digest before exec_module
- A parser.py modified after load-time validation is rejected
- A parser.py with no checksum is allowed (with warning) when enforcement is off
- A parser.py with no checksum is blocked when enforce_plugin_signatures is on
- A parser.py where the checksum matches is allowed
- Executor skips exec_module when verify_parser_at_exec_time returns False
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
        monkeypatch.setattr(settings, "enforce_plugin_signatures", False)
        parser_src = "def parse(output): return {'findings': []}\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)

        mgr = _make_manager(tmp_path)
        # Load the checksum from the written metadata
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        plugin = _minimal_plugin_meta(checksum=metadata["checksum"])

        assert mgr.verify_parser_at_exec_time(plugin, plugin_dir) is True

    def test_tampered_parser_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "enforce_plugin_signatures", False)
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
        monkeypatch.setattr(settings, "enforce_plugin_signatures", False)
        plugin_dir, _ = _write_plugin(tmp_path, parser_src="", include_checksum=False)
        plugin = _minimal_plugin_meta(checksum=None)

        mgr = _make_manager(tmp_path)
        assert mgr.verify_parser_at_exec_time(plugin, plugin_dir) is True

    def test_no_checksum_blocked_when_enforcement_on(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "enforce_plugin_signatures", True)
        plugin_dir, _ = _write_plugin(tmp_path, parser_src="", include_checksum=False)
        plugin = _minimal_plugin_meta(checksum=None)

        mgr = _make_manager(tmp_path)
        assert mgr.verify_parser_at_exec_time(plugin, plugin_dir) is False

    def test_digest_compute_failure_returns_false(self, tmp_path, monkeypatch):
        """If the digest computation raises (e.g. permissions), reject execution."""
        monkeypatch.setattr(settings, "enforce_plugin_signatures", False)
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
    def test_exec_module_skipped_when_integrity_fails(self, tmp_path, monkeypatch):
        """When verify_parser_at_exec_time returns False the parser must not run."""
        monkeypatch.setattr(settings, "enforce_plugin_signatures", False)

        parser_src = "def parse(output): return {'findings': []}\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)
        metadata = json.loads((plugin_dir / "metadata.json").read_text())

        # Tamper with parser.py so the digest no longer matches
        (plugin_dir / "parser.py").write_text(
            "import sys; sys.exit(99)\ndef parse(output): return {}\n",
            encoding="utf-8",
        )

        from backend.secuscan.models import PluginMetadata
        plugin = _minimal_plugin_meta(checksum=metadata["checksum"])

        mgr = _make_manager(tmp_path)
        mgr.plugins_dir = tmp_path
        mgr.plugins[plugin.id] = plugin

        exec_called = []

        original_exec = __builtins__.__class__.__dict__  # not used
        import importlib.util as ilu

        original_exec_module = None

        class _CapturingLoader:
            def exec_module(self, module):
                exec_called.append(True)

        with patch("importlib.util.spec_from_file_location") as mock_spec:
            mock_loader = MagicMock()
            mock_loader.exec_module = MagicMock(side_effect=lambda m: exec_called.append(True))
            mock_spec_obj = MagicMock()
            mock_spec_obj.loader = mock_loader
            mock_spec.return_value = mock_spec_obj

            with patch("importlib.util.module_from_spec", return_value=MagicMock()):
                # Import executor lazily to avoid circular-import issues at module level
                from backend.secuscan import executor as executor_module

                plugin_obj = plugin
                # Directly call _parse_results, patching plugin_manager
                exec_instance = executor_module.TaskExecutor.__new__(executor_module.TaskExecutor)

                with patch(
                    "backend.secuscan.executor.get_plugin_manager", return_value=mgr
                ):
                    result = exec_instance._parse_results(plugin_obj, "raw output")

        assert len(exec_called) == 0, "exec_module must not be called when integrity check fails"

    def test_exec_module_called_when_integrity_passes(self, tmp_path, monkeypatch):
        """When verify_parser_at_exec_time returns True, exec_module must run."""
        monkeypatch.setattr(settings, "enforce_plugin_signatures", False)

        parser_src = "def parse(output):\n    return {'findings': []}\n"
        plugin_dir, _ = _write_plugin(tmp_path, parser_src=parser_src, include_checksum=True)
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        plugin = _minimal_plugin_meta(checksum=metadata["checksum"])

        mgr = _make_manager(tmp_path)
        mgr.plugins_dir = tmp_path
        mgr.plugins[plugin.id] = plugin

        exec_called = []

        def _fake_exec(module):
            exec_called.append(True)
            module.parse = lambda output: {"findings": []}

        with patch("importlib.util.spec_from_file_location") as mock_spec:
            mock_loader = MagicMock()
            mock_loader.exec_module = MagicMock(side_effect=_fake_exec)
            mock_spec_obj = MagicMock()
            mock_spec_obj.loader = mock_loader
            mock_spec.return_value = mock_spec_obj

            fake_module = MagicMock()
            fake_module.parse = lambda output: {"findings": []}

            with patch("importlib.util.module_from_spec", return_value=fake_module):
                from backend.secuscan import executor as executor_module
                exec_instance = executor_module.TaskExecutor.__new__(executor_module.TaskExecutor)

                with patch(
                    "backend.secuscan.executor.get_plugin_manager", return_value=mgr
                ):
                    result = exec_instance._parse_results(plugin, "raw output")

        assert len(exec_called) == 1, "exec_module must be called once when integrity check passes"
