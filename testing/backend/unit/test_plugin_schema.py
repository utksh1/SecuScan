"""
Tests for versioned plugin metadata schema and migration helpers.
"""

import pytest
from backend.secuscan.plugin_schema import (
    detect_schema_version,
    validate_by_version,
    validate_v1,
    validate_v2,
    migrate_v1_to_v2,
    migrate_to_latest,
    LATEST_SCHEMA_VERSION,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_v1():
    return {
        "id": "nmap",
        "name": "Nmap",
        "version": "1.0.0",
        "description": "Port scanner",
        "category": "recon",
        "engine": {"type": "cli", "binary": "nmap"},
        "command_template": ["nmap", "{target}"],
        "fields": [{"id": "target", "label": "Target", "type": "string"}],
        "output": {"parser": "custom"},
        "safety": {"level": "safe"},
        "checksum": "a" * 64,
    }


@pytest.fixture
def valid_v2(valid_v1):
    data = dict(valid_v1)
    data["schema_version"] = 2
    data["presets"] = {}
    data["learning"] = {}
    data["dependencies"] = {"binaries": [], "python_packages": []}
    return data


# ── detect_schema_version ─────────────────────────────────────────────────────

def test_detect_version_missing_defaults_to_1(valid_v1):
    assert detect_schema_version(valid_v1) == 1


def test_detect_version_explicit(valid_v2):
    assert detect_schema_version(valid_v2) == 2


# ── validate_v1 ───────────────────────────────────────────────────────────────

def test_validate_v1_valid(valid_v1):
    assert validate_v1(valid_v1) == []


def test_validate_v1_missing_field(valid_v1):
    del valid_v1["engine"]
    errors = validate_v1(valid_v1)
    assert any("engine" in e for e in errors)


# ── validate_v2 ───────────────────────────────────────────────────────────────

def test_validate_v2_valid(valid_v2):
    assert validate_v2(valid_v2) == []


def test_validate_v2_wrong_version(valid_v1):
    valid_v1["schema_version"] = 1
    errors = validate_v2(valid_v1)
    assert any("schema_version" in e for e in errors)


# ── validate_by_version ───────────────────────────────────────────────────────

def test_validate_by_version_v1(valid_v1):
    assert validate_by_version(valid_v1) == []


def test_validate_by_version_v2(valid_v2):
    assert validate_by_version(valid_v2) == []


def test_validate_by_version_unknown():
    errors = validate_by_version({"schema_version": 99})
    assert any("Unknown" in e for e in errors)


# ── migrate_v1_to_v2 ─────────────────────────────────────────────────────────

def test_migrate_v1_to_v2_sets_version(valid_v1):
    result = migrate_v1_to_v2(valid_v1)
    assert result["schema_version"] == 2


def test_migrate_v1_to_v2_adds_presets(valid_v1):
    result = migrate_v1_to_v2(valid_v1)
    assert "presets" in result


def test_migrate_v1_to_v2_adds_dependencies(valid_v1):
    result = migrate_v1_to_v2(valid_v1)
    assert "dependencies" in result
    assert "binaries" in result["dependencies"]


def test_migrate_v1_to_v2_does_not_mutate_original(valid_v1):
    original = dict(valid_v1)
    migrate_v1_to_v2(valid_v1)
    assert valid_v1 == original


# ── migrate_to_latest ────────────────────────────────────────────────────────

def test_migrate_to_latest_from_v1(valid_v1):
    result = migrate_to_latest(valid_v1)
    assert result["schema_version"] == LATEST_SCHEMA_VERSION


def test_migrate_to_latest_already_latest(valid_v2):
    result = migrate_to_latest(valid_v2)
    assert result["schema_version"] == LATEST_SCHEMA_VERSION


def test_migrate_to_latest_validates_after_migration(valid_v1):
    result = migrate_to_latest(valid_v1)
    errors = validate_by_version(result)
    assert errors == []