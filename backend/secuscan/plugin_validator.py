"""
plugin_validator.py — SecuScan plugin metadata validator

Shared validation logic used by:
  - scripts/validate_plugins.py  (CLI helper for contributors)
  - backend plugin loading        (via PluginManager._validate_plugin)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ENGINE_TYPES = {"cli", "python", "docker"}
VALID_SAFETY_LEVELS = {"safe", "intrusive", "exploit"}
VALID_FIELD_TYPES = {"string","integer","text", "number", "boolean", "select", "multiselect", "textarea"}
VALID_PARSER_TYPES = {"json", "text", "custom", "none"}
CURRENT_SCHEMA_VERSION = 2
REQUIRED_TOP_LEVEL_FIELDS = [
    "id",
    "name",
    "description",
    "version",
    "category",
    "icon",
    "engine",
    "command_template",
    "fields",
    "output",
    "safety",
    "checksum",
]

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationError:
    plugin_id: str
    path: str
    message: str

    def display(self) -> str:
        return f"  ✗  [{self.plugin_id}]  {self.path}  →  {self.message}"


@dataclass
class ValidationResult:
    plugin_id: str
    plugin_dir: Path
    errors: list = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def add(self, path: str, message: str) -> None:
        self.errors.append(ValidationError(self.plugin_id, path, message))


# ---------------------------------------------------------------------------
# Core validator
# ---------------------------------------------------------------------------


class PluginMetadataValidator:
    """
    Validates a single plugin directory.

    Usage::

        validator = PluginMetadataValidator(Path("plugins/nmap"))
        result = validator.validate()
        if not result.valid:
            for err in result.errors:
                print(err.display())
    """

    def __init__(self, plugin_dir: Path) -> None:
        self.plugin_dir = plugin_dir
        self.metadata_file = plugin_dir / "metadata.json"

    def validate(self) -> ValidationResult:
        plugin_id = self.plugin_dir.name  # fallback before we parse id

        if not self.metadata_file.exists():
            result = ValidationResult(plugin_id=plugin_id, plugin_dir=self.plugin_dir)
            result.add("metadata.json", "File not found")
            return result

        try:
            raw = self.metadata_file.read_text(encoding="utf-8")
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            result = ValidationResult(plugin_id=plugin_id, plugin_dir=self.plugin_dir)
            result.add("metadata.json", f"Invalid JSON — {exc}")
            return result

        plugin_id = data.get("id") or plugin_id
        result = ValidationResult(plugin_id=plugin_id, plugin_dir=self.plugin_dir)

        self._check_required_fields(data, result)
        self._check_schema_version(data, result)
        self._check_engine(data, result)
        self._check_command_template(data, result)
        self._check_fields(data, result)
        self._check_output(data, result)
        self._check_safety(data, result)
        self._check_validation_block(data, result)
        self._check_checksum(data, result)
        self._check_dependencies(data, result)
        self._check_custom_parser(data, result)

        return result

    def _check_schema_version(self, data: dict, result: ValidationResult) -> None:
        version = data.get("schema_version")
        if version is None:
            return  # Legacy v1 plugins — schema_version is optional
        elif not isinstance(version, int) or version < 1:
            result.add("schema_version", f"'schema_version' must be a positive integer, got {version!r}")
        elif version > CURRENT_SCHEMA_VERSION:
            result.add(
                "schema_version",
                f"'schema_version' {version} is newer than supported version {CURRENT_SCHEMA_VERSION}.",
            )
        self._check_engine(data, result)
        self._check_command_template(data, result)
        self._check_fields(data, result)
        self._check_output(data, result)
        self._check_safety(data, result)
        self._check_validation_block(data, result)
        self._check_checksum(data, result)
        self._check_dependencies(data, result)
        self._check_custom_parser(data, result)

        return result

    def _check_required_fields(self, data: dict, result: ValidationResult) -> None:
        for key in REQUIRED_TOP_LEVEL_FIELDS:
            if key not in data or data[key] in (None, "", [], {}):
                result.add(key, f"Required field '{key}' is missing or empty")

    def _check_engine(self, data: dict, result: ValidationResult) -> None:
        engine = data.get("engine")
        if not isinstance(engine, dict):
            result.add("engine", "Must be an object")
            return

        engine_type = engine.get("type")
        if engine_type not in VALID_ENGINE_TYPES:
            result.add(
                "engine.type",
                f"'{engine_type}' is not a supported engine type — "
                f"must be one of: {sorted(VALID_ENGINE_TYPES)}",
            )

        if engine_type == "cli" and not engine.get("binary"):
            result.add("engine.binary", "CLI engine must declare a 'binary'")

        if engine_type == "docker" and not engine.get("image"):
            result.add("engine.image", "Docker engine must declare an 'image'")

    def _check_command_template(self, data: dict, result: ValidationResult) -> None:
        template = data.get("command_template")
        if not isinstance(template, list):
            result.add("command_template", "Must be a list of strings")
            return

        known_field_ids: set[str] = set()
        for f in data.get("fields", []):
            if isinstance(f, dict) and f.get("id"):
                known_field_ids.add(f["id"])

        placeholder_re = re.compile(r"\{(\w+)(?::[^}]*)?\}")
        for i, token in enumerate(template):
            if not isinstance(token, str):
                result.add(f"command_template[{i}]", "Each token must be a string")
                continue

            if token.startswith("--if:"):
                continue

            for match in placeholder_re.finditer(token):
                var_name = match.group(1)
                if known_field_ids and var_name not in known_field_ids:
                    result.add(
                        f"command_template[{i}]",
                        f"Placeholder '{{{var_name}}}' does not match any declared field id",
                    )

    def _check_fields(self, data: dict, result: ValidationResult) -> None:
        fields = data.get("fields")
        if not isinstance(fields, list):
            result.add("fields", "Must be a list")
            return

        seen_ids: set[str] = set()
        for i, f in enumerate(fields):
            prefix = f"fields[{i}]"
            if not isinstance(f, dict):
                result.add(prefix, "Each field must be an object")
                continue

            fid = f.get("id")
            if not fid:
                result.add(f"{prefix}.id", "Field is missing an 'id'")
            elif fid in seen_ids:
                result.add(f"{prefix}.id", f"Duplicate field id '{fid}'")
            else:
                seen_ids.add(fid)

            if not f.get("label"):
                result.add(f"{prefix}.label", f"Field '{fid}' is missing a 'label'")

            ftype = f.get("type")
            if ftype not in VALID_FIELD_TYPES:
                result.add(
                    f"{prefix}.type",
                    f"'{ftype}' is not a supported field type — "
                    f"must be one of: {sorted(VALID_FIELD_TYPES)}",
                )

            if ftype in ("select", "multiselect"):
                options = f.get("options")
                if not isinstance(options, list) or len(options) == 0:
                    result.add(
                        f"{prefix}.options",
                        f"Field '{fid}' is type '{ftype}' and must have a non-empty 'options' list",
                    )

    def _check_output(self, data: dict, result: ValidationResult) -> None:
        output = data.get("output")
        if not isinstance(output, dict):
            result.add("output", "Must be an object")
            return

        parser = output.get("parser")
        if parser not in VALID_PARSER_TYPES:
            result.add(
                "output.parser",
                f"'{parser}' is not a supported parser type — "
                f"must be one of: {sorted(VALID_PARSER_TYPES)}",
            )

    def _check_safety(self, data: dict, result: ValidationResult) -> None:
        safety = data.get("safety")
        if not isinstance(safety, dict):
            result.add("safety", "Must be an object")
            return

        level = safety.get("level")
        if level not in VALID_SAFETY_LEVELS:
            result.add(
                "safety.level",
                f"'{level}' is not a supported safety level — "
                f"must be one of: {sorted(VALID_SAFETY_LEVELS)}",
            )

        if safety.get("requires_consent") and not safety.get("consent_message"):
            result.add(
                "safety.consent_message",
                "Plugin requires consent but 'consent_message' is missing or empty",
            )

    def _check_validation_block(self, data: dict, result: ValidationResult) -> None:
        validation = data.get("validation")
        if validation is None:
            return

        if not isinstance(validation, dict):
            result.add("validation", "Must be an object if present")
            return

        for key, rule in validation.items():
            prefix = f"validation.{key}"
            if not isinstance(rule, dict):
                result.add(prefix, "Each validation rule must be an object")
                continue
            if "required" in rule and not isinstance(rule["required"], bool):
                result.add(f"{prefix}.required", "'required' must be a boolean")

    def _check_checksum(self, data: dict, result: ValidationResult) -> None:
        checksum = data.get("checksum")
        if not checksum:
            result.add("checksum", "Checksum is missing — run: python scripts/refresh_plugin_checksum.py --plugin <id>")
            return

        if not isinstance(checksum, str) or len(checksum) != 64:
            result.add(
                "checksum",
                "Checksum must be a 64-character SHA-256 hex string — "
                "run: python scripts/refresh_plugin_checksum.py --plugin <id>",
            )

    def _check_dependencies(self, data: dict, result: ValidationResult) -> None:
        deps = data.get("dependencies")
        if deps is None:
            return

        if not isinstance(deps, dict):
            result.add("dependencies", "Must be an object if present")
            return

        binaries = deps.get("binaries")
        if binaries is not None and not isinstance(binaries, list):
            result.add("dependencies.binaries", "Must be a list of strings")
        elif isinstance(binaries, list):
            for i, b in enumerate(binaries):
                if not isinstance(b, str) or not b.strip():
                    result.add(
                        f"dependencies.binaries[{i}]",
                        "Each binary dependency must be a non-empty string",
                    )

        python_packages = deps.get("python_packages")
        if python_packages is not None and not isinstance(python_packages, list):
            result.add("dependencies.python_packages", "Must be a list of strings")

    def _check_custom_parser(self, data: dict, result: ValidationResult) -> None:
        output = data.get("output")
        if not isinstance(output, dict):
            return

        if output.get("parser") == "custom":
            parser_file = self.plugin_dir / "parser.py"
            if not parser_file.exists():
                result.add(
                    "output.parser",
                    "Parser is 'custom' but parser.py was not found in the plugin directory",
                )


# ---------------------------------------------------------------------------
# Batch validation helpers
# ---------------------------------------------------------------------------


def validate_all_plugins(plugins_dir: Path) -> list:
    """Validate every plugin directory under plugins_dir."""
    results = []
    if not plugins_dir.exists():
        raise FileNotFoundError(f"Plugins directory not found: {plugins_dir}")

    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        results.append(PluginMetadataValidator(plugin_dir).validate())

    return results


def validate_one_plugin(plugin_dir: Path) -> ValidationResult:
    """Validate a single plugin directory."""
    return PluginMetadataValidator(plugin_dir).validate()
