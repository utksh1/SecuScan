"""
Unit tests for NetworkPolicyEngine audit export and clear methods.

Tests export_audit_log (JSON + CSV) and clear_audit_entries.

The network_policy module requires mocking config at sys.modules level to avoid
importing the real config module which depends on FastAPI/Pydantic.
"""
import sys
import json
from unittest.mock import patch, MagicMock
import pytest

# ---------------------------------------------------------------------------
# Mock heavy dependencies BEFORE importing the module under test
# ---------------------------------------------------------------------------

mock_settings = MagicMock()
mock_settings.network_audit_log_file = "/tmp/secuscan_audit_export_test.log"
mock_settings.network_audit_max_entries = 1000
mock_settings.enforce_network_policy = False
mock_settings.network_denylist = []
mock_settings.network_allowlist = []
mock_settings.MANDATORY_DENYLIST = {}
mock_config = MagicMock()
mock_config.settings = mock_settings
mock_config.MANDATORY_DENYLIST = {}

_mock_mod = MagicMock()
_mock_mod.settings = mock_settings
_mock_mod.MANDATORY_DENYLIST = {}
sys.modules["backend.secuscan.config"] = _mock_mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

from backend.secuscan.network_policy import NetworkPolicyEngine


def _reset_singleton():
    """Reset the module-level singleton so tests get a fresh engine."""
    import backend.secuscan.network_policy as mod
    mod._policy_engine = None


def _make_mock_config():
    """Return a mock config object that NetworkPolicyEngine accepts."""
    mock_settings = MagicMock()
    mock_settings.network_audit_log_file = "/tmp/secuscan_audit_export_test.log"
    mock_settings.network_audit_max_entries = 1000
    mock_settings.enforce_network_policy = False
    mock_settings.network_denylist = []
    mock_settings.network_allowlist = []
    mock_settings.MANDATORY_DENYLIST = {}
    mock_cfg = MagicMock()
    mock_cfg.settings = mock_settings
    mock_cfg.MANDATORY_DENYLIST = {}
    return mock_cfg


class TestExportAuditLog:
    """Tests for NetworkPolicyEngine.export_audit_log."""

    def _engine_with_entries(self, mock_cfg):
        """Create an engine with some audit entries."""
        import backend.secuscan.network_policy as mod
        mod._policy_engine = None
        engine = NetworkPolicyEngine(
            mock_cfg.settings.network_audit_log_file,
            mock_cfg.settings.network_audit_max_entries,
        )
        engine.add_deny_rule("192.168.1.0/24", reason="test-deny")
        engine.check_access("192.168.1.50", 22, "test-plugin", task_id="task-001")
        engine.add_allow_rule("10.0.0.0/8", reason="test-allow")
        engine.check_access("10.1.2.3", 80, "test-plugin", task_id="task-002")
        return engine

    def test_json_export_returns_valid_json(self):
        """JSON export must be parseable by json.loads."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        engine = self._engine_with_entries(mock_cfg)
        result = engine.export_audit_log("json")
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    def test_json_export_contains_expected_fields(self):
        """Each JSON entry must have the expected audit fields."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        engine = self._engine_with_entries(mock_cfg)
        result = engine.export_audit_log("json")
        parsed = json.loads(result)
        for entry in parsed:
            assert "timestamp" in entry
            assert "plugin_id" in entry
            assert "task_id" in entry
            assert "action" in entry
            assert "dest_ip" in entry
            assert "dest_port" in entry
            assert "policy_matched" in entry

    def test_json_export_action_is_policy_action_string(self):
        """The action field must be one of the known policy action strings."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        engine = self._engine_with_entries(mock_cfg)
        result = engine.export_audit_log("json")
        parsed = json.loads(result)
        for entry in parsed:
            assert entry["action"] in ["allow", "deny", "blocked"]

    def test_csv_export_returns_valid_csv(self):
        """CSV export must have a header row and data rows."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        engine = self._engine_with_entries(mock_cfg)
        result = engine.export_audit_log("csv")
        lines = result.strip().split("\n")
        assert len(lines) >= 2

    def test_csv_export_header_is_present(self):
        """CSV must start with the correct column header."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        engine = self._engine_with_entries(mock_cfg)
        result = engine.export_audit_log("csv")
        header = result.strip().split("\n")[0]
        assert "timestamp" in header
        assert "plugin_id" in header
        assert "task_id" in header
        assert "action" in header

    def test_csv_export_data_rows_match_entry_count(self):
        """Number of CSV data rows must match the number of audit entries."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        engine = self._engine_with_entries(mock_cfg)
        entries = engine.get_audit_entries()
        result = engine.export_audit_log("csv")
        data_lines = result.strip().split("\n")[1:]
        assert len(data_lines) == len(entries)

    def test_empty_audit_log_json_returns_empty_list(self):
        """export_audit_log('json') on an empty log returns '[]'."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        import backend.secuscan.network_policy as mod
        mod._policy_engine = None
        engine = NetworkPolicyEngine(
            mock_cfg.settings.network_audit_log_file,
            mock_cfg.settings.network_audit_max_entries,
        )
        result = engine.export_audit_log("json")
        assert result.strip() == "[]"

    def test_empty_audit_log_csv_returns_header_only(self):
        """export_audit_log('csv') on an empty log returns only the header."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        import backend.secuscan.network_policy as mod
        mod._policy_engine = None
        engine = NetworkPolicyEngine(
            mock_cfg.settings.network_audit_log_file,
            mock_cfg.settings.network_audit_max_entries,
        )
        result = engine.export_audit_log("csv")
        lines = result.strip().split("\n")
        assert len(lines) == 1


class TestClearAuditEntries:
    """Tests for NetworkPolicyEngine.clear_audit_entries."""

    def _engine_with_entries(self, mock_cfg):
        """Create an engine with some audit entries."""
        import backend.secuscan.network_policy as mod
        mod._policy_engine = None
        engine = NetworkPolicyEngine(
            mock_cfg.settings.network_audit_log_file,
            mock_cfg.settings.network_audit_max_entries,
        )
        engine.add_deny_rule("192.168.1.0/24", reason="test-deny")
        engine.check_access("192.168.1.50", 22, "test-plugin", task_id="task-old")
        return engine

    def test_clear_removes_all_entries(self):
        """clear_audit_entries must remove all entries from the engine."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        engine = self._engine_with_entries(mock_cfg)
        assert len(engine.get_audit_entries()) > 0
        engine.clear_audit_entries()
        assert len(engine.get_audit_entries()) == 0

    def test_clear_on_empty_log_is_safe(self):
        """clear_audit_entries on an already-empty log must not raise."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        import backend.secuscan.network_policy as mod
        mod._policy_engine = None
        engine = NetworkPolicyEngine(
            mock_cfg.settings.network_audit_log_file,
            mock_cfg.settings.network_audit_max_entries,
        )
        engine.clear_audit_entries()  # Must not raise
        assert len(engine.get_audit_entries()) == 0

    def test_entries_after_clear_are_independent(self):
        """After clearing, adding new entries should work normally."""
        _reset_singleton()
        mock_cfg = _make_mock_config()
        engine = self._engine_with_entries(mock_cfg)
        engine.clear_audit_entries()

        engine.add_allow_rule("192.168.0.0/16", reason="new-rule")
        engine.check_access("192.168.1.1", 80, "another-plugin", task_id="task-new")

        entries = engine.get_audit_entries()
        assert len(entries) == 1
        assert entries[0].task_id == "task-new"
