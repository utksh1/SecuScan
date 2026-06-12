"""
plugin_schema.py — Versioned plugin metadata schema with migration helpers.

Supports schema_version field on plugin metadata and provides:
  - Version-aware validation
  - Migration helpers to upgrade old plugin metadata to latest schema
  - Docs for updating old plugin metadata
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

LATEST_SCHEMA_VERSION = 2

# Fields added in each version (for migration reference)
VERSION_CHANGELOG = {
    1: "Initial schema: id, name, version, description, category, engine, "
       "command_template, fields, output, safety, checksum.",
    2: "Added schema_version field. Added presets block. "
       "Added learning block. Added dependencies block.",
}


# ── Schema version detector ───────────────────────────────────────────────────

def detect_schema_version(metadata: dict[str, Any]) -> int:
    """
    Return the declared schema_version, or infer it for legacy plugins.

    Legacy plugins (no schema_version key) are treated as version 1.
    """
    return int(metadata.get("schema_version", 1))


# ── Validators by version ─────────────────────────────────────────────────────

def validate_v1(metadata: dict[str, Any]) -> list[str]:
    """Validate v1 required fields. Returns list of error strings."""
    errors: list[str] = []
    required = ["id", "name", "version", "description", "category",
                "engine", "command_template", "fields", "output", "safety"]
    for key in required:
        if not metadata.get(key):
            errors.append(f"v1: missing required field '{key}'")
    return errors


def validate_v2(metadata: dict[str, Any]) -> list[str]:
    """Validate v2 fields on top of v1. Returns list of error strings."""
    errors = validate_v1(metadata)
    if metadata.get("schema_version") != 2:
        errors.append("v2: 'schema_version' must be 2")
    return errors


_VALIDATORS = {
    1: validate_v1,
    2: validate_v2,
}


def validate_by_version(metadata: dict[str, Any]) -> list[str]:
    """
    Detect schema version and run the matching validator.

    Returns a list of error strings (empty = valid).
    """
    version = detect_schema_version(metadata)
    validator = _VALIDATORS.get(version)
    if validator is None:
        return [f"Unknown schema_version '{version}'. "
                f"Supported: {sorted(_VALIDATORS)}"]
    return validator(metadata)


# ── Migration helpers ─────────────────────────────────────────────────────────

def migrate_v1_to_v2(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Migrate a v1 plugin metadata dict to v2 in-place (on a copy).

    Changes applied:
      - Sets schema_version = 2
      - Adds empty presets block if missing
      - Adds empty learning block if missing
      - Adds empty dependencies block if missing
    """
    data = copy.deepcopy(metadata)
    data["schema_version"] = 2

    if "presets" not in data:
        data["presets"] = {}
        logger.debug("migrate_v1_to_v2: added empty 'presets' block")

    if "learning" not in data:
        data["learning"] = {}
        logger.debug("migrate_v1_to_v2: added empty 'learning' block")

    if "dependencies" not in data:
        data["dependencies"] = {"binaries": [], "python_packages": []}
        logger.debug("migrate_v1_to_v2: added empty 'dependencies' block")

    return data


_MIGRATIONS = {
    (1, 2): migrate_v1_to_v2,
}


def migrate_to_latest(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Migrate metadata from its current version to LATEST_SCHEMA_VERSION.

    Applies migrations in sequence (1→2, 2→3, …).
    Returns a new dict; the original is not modified.
    """
    data = copy.deepcopy(metadata)
    current = detect_schema_version(data)

    while current < LATEST_SCHEMA_VERSION:
        next_version = current + 1
        migration_fn = _MIGRATIONS.get((current, next_version))
        if migration_fn is None:
            raise ValueError(
                f"No migration path from v{current} to v{next_version}."
            )
        data = migration_fn(data)
        logger.info("Plugin schema migrated: v%d → v%d", current, next_version)
        current = next_version

    return data


# ── File-level helpers ────────────────────────────────────────────────────────

def load_and_migrate(metadata_path: Path) -> dict[str, Any]:
    """
    Load a metadata.json file, migrate it to the latest schema, and return it.
    Does NOT write the migrated data back to disk.
    """
    raw = metadata_path.read_text(encoding="utf-8")
    metadata = json.loads(raw)
    return migrate_to_latest(metadata)


def validate_file(metadata_path: Path) -> list[str]:
    """
    Load a metadata.json file and validate it against its declared schema version.
    Returns a list of error strings (empty = valid).
    """
    raw = metadata_path.read_text(encoding="utf-8")
    metadata = json.loads(raw)
    return validate_by_version(metadata)