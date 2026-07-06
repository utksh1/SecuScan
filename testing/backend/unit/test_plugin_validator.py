"""
Unit tests for backend/secuscan/plugin_validator.py

Run with:
    pytest testing/backend/unit/test_plugin_validator.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make sure repo root is on sys.path when running from any working directory.
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import (
    PluginMetadataValidator,
    ValidationResult,
    validate_all_plugins,
    validate_one_plugin,
    VALID_ENGINE_TYPES,
    VALID_SAFETY_LEVELS,
    VALID_FIELD_TYPES,
    VALID_PARSER_TYPES,
    VALID_CATEGORIES,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "plugins"
VALID_FIXTURE = FIXTURES_DIR / "valid_plugin"
INVALID_FIXTURE = FIXTURES_DIR / "invalid_plugin"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_paths(result: ValidationResult) -> set[str]:
    return {e.path for e in result.errors}


def _error_messages(result: ValidationResult) -> list[str]:
    return [e.message for e in result.errors]


def _write_metadata(tmp_path: Path, data: dict) -> Path:
    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / "metadata.json").write_text(json.dumps(data), encoding="utf-8")
    return plugin_dir


def _minimal_valid() -> dict:
    """Return a minimal metadata dict that passes all checks."""
    return {
        "id": "test_ping",
        "name": "Test Ping",
        "description": "Fixture plugin.",
        "version": "1.0.0",
        "category": "utils",
        "icon": "ping",
        "engine": {"type": "cli", "binary": "ping"},
        "command_template": ["ping", "-c", "{count}", "{target}"],
        "fields": [
            {"id": "target", "label": "Target Host", "type": "text", "help": "IP address or hostname"},
            {"id": "count", "label": "Count", "type": "number", "help": "Number of packets"},
        ],
        "output": {"parser": "text"},
        "safety": {"level": "safe", "requires_consent": False},
        "checksum": "a" * 64,
    }


# ===========================================================================
# Fixture-based smoke tests
# ===========================================================================


class TestFixtures:
    def test_valid_fixture_passes(self):
        result = validate_one_plugin(VALID_FIXTURE)
        # The fixture uses a placeholder checksum so we expect exactly that error.
        # All other checks should pass.
        non_checksum_errors = [e for e in result.errors if e.path != "checksum"]
        assert non_checksum_errors == [], (
            f"Unexpected errors in valid fixture: {non_checksum_errors}"
        )

    def test_invalid_fixture_fails(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        assert not result.valid, "Invalid fixture should fail validation"
        assert len(result.errors) >= 5, (
            f"Expected at least 5 errors, got {len(result.errors)}: {result.errors}"
        )

    def test_invalid_fixture_catches_bad_engine_type(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        assert "engine.type" in _error_paths(result)

    def test_invalid_fixture_catches_bad_safety_level(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        assert "safety.level" in _error_paths(result)

    def test_invalid_fixture_catches_missing_name(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        assert "name" in _error_paths(result)

    def test_invalid_fixture_catches_missing_checksum(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        assert "checksum" in _error_paths(result)

    def test_invalid_fixture_catches_custom_parser_without_file(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        assert "output.parser" in _error_paths(result)

    def test_invalid_fixture_catches_duplicate_field_id(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        dup_errors = [e for e in result.errors if "Duplicate" in e.message]
        assert dup_errors, "Expected a duplicate field id error"

    def test_invalid_fixture_catches_select_without_options(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        opts_errors = [e for e in result.errors if "options" in e.path]
        assert opts_errors, "Expected an options-missing error for select field"

    def test_invalid_fixture_catches_consent_without_message(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        assert "safety.consent_message" in _error_paths(result)

    def test_invalid_fixture_catches_unknown_placeholder(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        placeholder_errors = [e for e in result.errors if "Placeholder" in e.message]
        assert placeholder_errors, "Expected placeholder-mismatch error"

    def test_invalid_fixture_catches_missing_help_text(self):
        result = validate_one_plugin(INVALID_FIXTURE)
        help_warnings = [e for e in result.warnings if e.path.endswith(".help")]
        assert len(help_warnings) >= 2, "Expected help text warnings for both fields"


# ===========================================================================
# Required fields
# ===========================================================================


class TestRequiredFields:
    @pytest.mark.parametrize("missing_key", [
        "id", "name", "description", "version", "category",
        "icon", "engine", "command_template", "fields", "output", "safety", "checksum",
    ])
    def test_missing_required_field_is_reported(self, tmp_path, missing_key):
        data = _minimal_valid()
        del data[missing_key]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert missing_key in _error_paths(result), (
            f"Expected error for missing key '{missing_key}', got: {_error_paths(result)}"
        )

    def test_empty_string_name_is_reported(self, tmp_path):
        data = _minimal_valid()
        data["name"] = ""
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "name" in _error_paths(result)


# ===========================================================================
# Engine
# ===========================================================================


class TestEngine:
    @pytest.mark.parametrize("engine_type", list(VALID_ENGINE_TYPES))
    def test_valid_engine_types_accepted(self, tmp_path, engine_type):
        data = _minimal_valid()
        data["engine"] = {"type": engine_type, "binary": "tool"}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "engine.type" not in _error_paths(result)

    def test_invalid_engine_type_reported(self, tmp_path):
        data = _minimal_valid()
        data["engine"] = {"type": "quantum"}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "engine.type" in _error_paths(result)

    def test_cli_engine_without_binary_reported(self, tmp_path):
        data = _minimal_valid()
        data["engine"] = {"type": "cli"}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "engine.binary" in _error_paths(result)

    def test_docker_engine_without_image_reported(self, tmp_path):
        data = _minimal_valid()
        data["engine"] = {"type": "docker"}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "engine.image" in _error_paths(result)

    def test_engine_not_dict_reported(self, tmp_path):
        data = _minimal_valid()
        data["engine"] = "cli"
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "engine" in _error_paths(result)


# ===========================================================================
# Command template
# ===========================================================================


class TestCommandTemplate:
    def test_placeholder_matching_declared_field_is_ok(self, tmp_path):
        data = _minimal_valid()
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        ct_errors = [e for e in result.errors if e.path.startswith("command_template")]
        assert ct_errors == []

    def test_unknown_placeholder_reported(self, tmp_path):
        data = _minimal_valid()
        data["command_template"] = ["tool", "{ghost_field}"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        ct_errors = [e for e in result.errors if "ghost_field" in e.message]
        assert ct_errors, "Expected error for undeclared placeholder"

    def test_conditional_token_not_flagged_as_unknown(self, tmp_path):
        data = _minimal_valid()
        data["command_template"] = ["tool", "--if:count:then:-c:{count}"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        ct_errors = [e for e in result.errors if e.path.startswith("command_template")]
        assert ct_errors == []

    def test_non_list_command_template_reported(self, tmp_path):
        data = _minimal_valid()
        data["command_template"] = "ping -c 4 {target}"
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "command_template" in _error_paths(result)


# ===========================================================================
# Fields
# ===========================================================================


class TestFields:
    @pytest.mark.parametrize("ftype", list(VALID_FIELD_TYPES))
    def test_valid_field_types_accepted(self, tmp_path, ftype):
        data = _minimal_valid()
        field_def = {"id": "x", "label": "X", "type": ftype}
        if ftype in ("select", "multiselect"):
            field_def["options"] = ["a", "b"]
        data["fields"] = [field_def]
        data["command_template"] = ["tool"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        type_errors = [e for e in result.errors if "fields[0].type" in e.path]
        assert type_errors == []

    def test_invalid_field_type_reported(self, tmp_path):
        data = _minimal_valid()
        data["fields"] = [{"id": "x", "label": "X", "type": "slider"}]
        data["command_template"] = ["tool"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "fields[0].type" in _error_paths(result)

    def test_duplicate_field_id_reported(self, tmp_path):
        data = _minimal_valid()
        data["fields"] = [
            {"id": "target", "label": "Target", "type": "text"},
            {"id": "target", "label": "Target Again", "type": "text"},
        ]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        dup = [e for e in result.errors if "Duplicate" in e.message]
        assert dup

    def test_select_without_options_reported(self, tmp_path):
        data = _minimal_valid()
        data["fields"] = [{"id": "mode", "label": "Mode", "type": "select"}]
        data["command_template"] = ["tool"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        opts_errors = [e for e in result.errors if "options" in e.path]
        assert opts_errors

    def test_multiselect_without_options_reported(self, tmp_path):
        data = _minimal_valid()
        data["fields"] = [{"id": "tags", "label": "Tags", "type": "multiselect"}]
        data["command_template"] = ["tool"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        opts_errors = [e for e in result.errors if "options" in e.path]
        assert opts_errors

    def test_missing_field_label_reported(self, tmp_path):
        data = _minimal_valid()
        data["fields"] = [{"id": "target", "type": "text"}]
        data["command_template"] = ["tool", "{target}"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        label_errors = [e for e in result.errors if "label" in e.path]
        assert label_errors


# ===========================================================================
# Output / parser
# ===========================================================================


class TestOutput:
    @pytest.mark.parametrize("parser", list(VALID_PARSER_TYPES))
    def test_valid_parser_types_accepted(self, tmp_path, parser):
        data = _minimal_valid()
        data["output"] = {"parser": parser}
        plugin_dir = _write_metadata(tmp_path, data)
        if parser == "custom":
            (plugin_dir / "parser.py").write_text("# stub", encoding="utf-8")
        result = validate_one_plugin(plugin_dir)
        parser_errors = [e for e in result.errors if e.path == "output.parser"]
        assert parser_errors == []

    def test_invalid_parser_type_reported(self, tmp_path):
        data = _minimal_valid()
        data["output"] = {"parser": "magic"}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "output.parser" in _error_paths(result)

    def test_custom_parser_without_file_reported(self, tmp_path):
        data = _minimal_valid()
        data["output"] = {"parser": "custom"}
        plugin_dir = _write_metadata(tmp_path, data)
        # Do NOT create parser.py
        result = validate_one_plugin(plugin_dir)
        assert "output.parser" in _error_paths(result)

    def test_custom_parser_with_file_is_ok(self, tmp_path):
        data = _minimal_valid()
        data["output"] = {"parser": "custom"}
        plugin_dir = _write_metadata(tmp_path, data)
        (plugin_dir / "parser.py").write_text("# stub", encoding="utf-8")
        result = validate_one_plugin(plugin_dir)
        parser_errors = [e for e in result.errors if e.path == "output.parser"]
        assert parser_errors == []


# ===========================================================================
# Safety
# ===========================================================================


class TestSafety:
    @pytest.mark.parametrize("level", list(VALID_SAFETY_LEVELS))
    def test_valid_safety_levels_accepted(self, tmp_path, level):
        data = _minimal_valid()
        data["safety"] = {"level": level}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        safety_errors = [e for e in result.errors if e.path == "safety.level"]
        assert safety_errors == []

    def test_invalid_safety_level_reported(self, tmp_path):
        data = _minimal_valid()
        data["safety"] = {"level": "nuclear"}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "safety.level" in _error_paths(result)

    def test_requires_consent_without_message_reported(self, tmp_path):
        data = _minimal_valid()
        data["safety"] = {"level": "intrusive", "requires_consent": True}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "safety.consent_message" in _error_paths(result)

    def test_requires_consent_with_message_is_ok(self, tmp_path):
        data = _minimal_valid()
        data["safety"] = {
            "level": "intrusive",
            "requires_consent": True,
            "consent_message": "This plugin will probe the target actively.",
        }
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        consent_errors = [e for e in result.errors if "consent" in e.path]
        assert consent_errors == []


# ===========================================================================
# Checksum
# ===========================================================================


class TestChecksum:
    def test_missing_checksum_reported(self, tmp_path):
        data = _minimal_valid()
        del data["checksum"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "checksum" in _error_paths(result)

    def test_short_checksum_reported(self, tmp_path):
        data = _minimal_valid()
        data["checksum"] = "abc123"
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "checksum" in _error_paths(result)

    def test_correct_length_checksum_accepted(self, tmp_path):
        data = _minimal_valid()
        data["checksum"] = "b" * 64
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        checksum_errors = [e for e in result.errors if e.path == "checksum"]
        assert checksum_errors == []


# ===========================================================================
# Dependencies
# ===========================================================================


class TestDependencies:
    def test_valid_dependencies_block_is_ok(self, tmp_path):
        data = _minimal_valid()
        data["dependencies"] = {"binaries": ["curl", "jq"], "python_packages": ["requests"]}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        dep_errors = [e for e in result.errors if e.path.startswith("dependencies")]
        assert dep_errors == []

    def test_empty_binary_string_reported(self, tmp_path):
        data = _minimal_valid()
        data["dependencies"] = {"binaries": ["curl", ""]}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        dep_errors = [e for e in result.errors if "binaries[1]" in e.path]
        assert dep_errors

    def test_non_list_binaries_reported(self, tmp_path):
        data = _minimal_valid()
        data["dependencies"] = {"binaries": "curl"}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "dependencies.binaries" in _error_paths(result)

    def test_absent_dependencies_block_is_ok(self, tmp_path):
        data = _minimal_valid()
        data.pop("dependencies", None)
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        dep_errors = [e for e in result.errors if e.path.startswith("dependencies")]
        assert dep_errors == []


# ===========================================================================
# Validation block
# ===========================================================================


class TestValidationBlock:
    def test_absent_validation_block_is_ok(self, tmp_path):
        data = _minimal_valid()
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        val_errors = [e for e in result.errors if e.path.startswith("validation")]
        assert val_errors == []

    def test_non_dict_validation_block_reported(self, tmp_path):
        data = _minimal_valid()
        data["validation"] = ["target"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "validation" in _error_paths(result)

    def test_non_bool_required_reported(self, tmp_path):
        data = _minimal_valid()
        data["validation"] = {"target": {"required": "yes"}}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "validation.target.required" in _error_paths(result)

    def test_valid_validation_block_is_ok(self, tmp_path):
        data = _minimal_valid()
        data["validation"] = {"target": {"required": True}}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        val_errors = [e for e in result.errors if e.path.startswith("validation")]
        assert val_errors == []


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    def test_missing_metadata_json_reported(self, tmp_path):
        plugin_dir = tmp_path / "empty_plugin"
        plugin_dir.mkdir()
        result = validate_one_plugin(plugin_dir)
        assert not result.valid
        assert "metadata.json" in _error_paths(result)

    def test_invalid_json_reported(self, tmp_path):
        plugin_dir = tmp_path / "bad_json"
        plugin_dir.mkdir()
        (plugin_dir / "metadata.json").write_text("{bad json!!!", encoding="utf-8")
        result = validate_one_plugin(plugin_dir)
        assert not result.valid
        assert "metadata.json" in _error_paths(result)

    def test_validate_all_plugins_returns_results_for_each_dir(self, tmp_path):
        for name in ("plugin_a", "plugin_b"):
            d = tmp_path / name
            d.mkdir()
            (d / "metadata.json").write_text(json.dumps(_minimal_valid()), encoding="utf-8")
        results = validate_all_plugins(tmp_path)
        assert len(results) == 2

    def test_validate_all_plugins_nonexistent_dir_raises(self):
        with pytest.raises(FileNotFoundError):
            validate_all_plugins(Path("/nonexistent/plugins"))

    def test_error_display_format(self, tmp_path):
        data = _minimal_valid()
        data["safety"] = {"level": "bad"}
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        err = next(e for e in result.errors if e.path == "safety.level")
        display = err.display()
        assert "[" in display and "safety.level" in display and "→" in display


# ===========================================================================
# Metadata quality lint checks
# ===========================================================================


class TestMetadataQualityLint:
    def test_missing_field_help_text_reported_as_warning(self, tmp_path):
        data = _minimal_valid()
        data["fields"] = [
            {"id": "target", "label": "Target", "type": "text"},
        ]
        data["command_template"] = ["ping", "{target}"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        help_warnings = [e for e in result.warnings if e.path == "fields[0].help"]
        assert len(help_warnings) == 1
        assert "help" in help_warnings[0].message

    def test_field_help_text_present_no_warning(self, tmp_path):
        data = _minimal_valid()
        data["fields"] = [
            {"id": "target", "label": "Target", "type": "text", "help": "The target IP or hostname"},
        ]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        help_warnings = [e for e in result.warnings if e.path.startswith("fields[0].help")]
        assert help_warnings == []

    def test_invalid_category_reported(self, tmp_path):
        data = _minimal_valid()
        data["category"] = "unknown_category"
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        assert "category" in _error_paths(result)
        cat_errors = [e for e in result.errors if e.path == "category"]
        assert len(cat_errors) == 1
        assert "not a recognized category" in cat_errors[0].message

    def test_valid_categories_accepted(self, tmp_path):
        for cat in sorted(VALID_CATEGORIES):
            data = _minimal_valid()
            data["category"] = cat
            plugin_dir = _write_metadata(tmp_path, data)
            result = validate_one_plugin(plugin_dir)
            cat_errors = [e for e in result.errors if e.path == "category"]
            assert cat_errors == [], f"Category '{cat}' should be valid"

    def test_missing_category_is_not_flagged(self, tmp_path):
        data = _minimal_valid()
        del data["category"]
        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)
        cat_errors = [e for e in result.errors if e.path == "category"]
        assert len(cat_errors) == 1
        assert "Required" in cat_errors[0].message

    def test_mutually_exclusive_fields_must_reference_existing_fields(self, tmp_path):
        data = _minimal_valid()
        data["fields"] = [
            {
                "id": "password",
                "label": "Password",
                "type": "text",
                "help": "Password authentication",
            },
            {
                "id": "private_key",
                "label": "Private Key",
                "type": "text",
                "help": "SSH private key",
            },
        ]
        data["validation"] = {
            "authentication": {
                "mutually_exclusive": [
                    "password",
                    "private_key",
                ]
            }
        }

        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)

        mutually_exclusive_errors = [
            e
            for e in result.errors
            if "mutually_exclusive" in e.path
        ]

        assert mutually_exclusive_errors == []

    def test_mutually_exclusive_fields_unknown_field_is_rejected(self, tmp_path):
        data = _minimal_valid()
        data["fields"] = [
            {
                "id": "password",
                "label": "Password",
                "type": "text",
                "help": "Password authentication",
            },
        ]
        data["validation"] = {
            "authentication": {
                "mutually_exclusive": [
                    "password",
                    "private_key",
                ]
            }
        }

        plugin_dir = _write_metadata(tmp_path, data)
        result = validate_one_plugin(plugin_dir)

        assert not result.valid

        mutually_exclusive_errors = [
            e
            for e in result.errors
            if "mutually_exclusive" in e.path
        ]

        assert len(mutually_exclusive_errors) == 1
        assert "private_key" in mutually_exclusive_errors[0].message


# ===========================================================================
# Security negative tests
# ===========================================================================


class TestSecurityNegativeTests:
    def test_integrity_check_fails_on_checksum_mismatch(self, tmp_path):
        """PluginManager._verify_plugin_integrity should return False if checksum mismatches."""
        from backend.secuscan.plugins import PluginManager
        from backend.secuscan.models import PluginMetadata

        # 1. Create a valid metadata but with wrong checksum
        data = _minimal_valid()
        data["checksum"] = "b" * 64  # wrong checksum
        data["presets"] = {}
        for f in data["fields"]:
            if f["type"] == "number":
                f["type"] = "integer"
        plugin_dir = _write_metadata(tmp_path, data)

        plugin = PluginMetadata(**data)
        mgr = PluginManager(plugins_dir=str(tmp_path))

        assert mgr._verify_plugin_integrity(plugin, plugin_dir) is False

    def test_sandbox_exec_fails_on_exec_statement(self):
        """Parser sandbox should raise ParserSandboxError when parser execution encounters exec()."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox, ParserSandboxError

        fixture_dir = Path(__file__).resolve().parent / "fixtures" / "plugins" / "forbidden_parser_plugin"
        parser_path = fixture_dir / "parser.py"

        with pytest.raises(ParserSandboxError) as exc_info:
            run_parser_in_sandbox(
                parser_path=parser_path,
                plugin_id="forbidden_parser_plugin",
                parser_input="test input"
            )
        assert "ValueError" in exc_info.value.stderr_excerpt or "exec" in exc_info.value.stderr_excerpt or "sandbox exec test" in exc_info.value.stderr_excerpt

    def test_sandbox_strips_environ_secrets(self, monkeypatch):
        """Parser sandbox environment variables should be stripped to avoid secret leakage."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox

        # Set a sensitive secret in the parent process env
        monkeypatch.setenv("SECUSCAN_VAULT_KEY", "super_secret_credentials_xyz")

        # We can dynamically write a temp parser that checks the environment
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            parser_dir = Path(tmp_dir)
            parser_file = parser_dir / "parser.py"
            parser_file.write_text(
                "import os\n"
                "def parse(output):\n"
                "    secret = os.environ.get('SECUSCAN_VAULT_KEY')\n"
                "    return {'secret': secret}\n",
                encoding="utf-8"
            )

            result = run_parser_in_sandbox(
                parser_path=parser_file,
                plugin_id="env_leak_test_plugin",
                parser_input="test"
            )

            # The result dict should NOT contain the secret
            assert result.get("secret") is None or result.get("secret") == ""

    def test_sandbox_timeout_terminates_hanging_parser(self):
        """Parser sandbox should kill a hanging parser execution via timeout."""
        from backend.secuscan.parser_sandbox import run_parser_in_sandbox, ParserSandboxError
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            parser_dir = Path(tmp_dir)
            parser_file = parser_dir / "parser.py"
            parser_file.write_text(
                "import time\n"
                "def parse(output):\n"
                "    # Infinite loop to simulate socket hanging or blocking read\n"
                "    while True:\n"
                "        time.sleep(0.1)\n",
                encoding="utf-8"
            )

            # Set a very low timeout (e.g., 1 second) to run the test quickly
            with pytest.raises(ParserSandboxError) as exc_info:
                run_parser_in_sandbox(
                    parser_path=parser_file,
                    plugin_id="timeout_test_plugin",
                    parser_input="test",
                    timeout_seconds=1
                )

            assert "timed out" in str(exc_info.value)
