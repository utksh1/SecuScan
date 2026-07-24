import os
import sys
import tempfile
from pathlib import Path

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from scripts.validate_plugins_catalog import (
    parse_plugins_md,
    extract_counts_from_catalog,
    extract_category_counts_from_catalog,
    validate_catalog,
)


def test_parse_plugins_md_extracts_plugin_entries():
    catalog_content = """# Title

## Plugin Index

| Plugin | ID | Category | Safety | Primary Binary | Summary |
| --- | --- | --- | --- | --- | --- |
| Amass | `amass` | `recon` | `safe` | `amass` | Deep mapping. |
| Nuclei | `nuclei` | `vulnerability` | `intrusive` | `nuclei` | Fast scanner. |
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(catalog_content)
        path = Path(f.name)

    try:
        result = parse_plugins_md(path)
        assert "amass" in result
        assert result["amass"]["name"] == "Amass"
        assert result["amass"]["category"] == "recon"
        assert result["amass"]["safety"] == "safe"
        assert "nuclei" in result
        assert result["nuclei"]["category"] == "vulnerability"
        assert result["nuclei"]["safety"] == "intrusive"
    finally:
        path.unlink()


def test_parse_plugins_md_skips_header_row():
    catalog_content = """# Title

| Plugin | ID | Category | Safety | Primary Binary | Summary |
| --- | --- | --- | --- | --- | --- |
| Plugin | ID | Category | Safety | Primary Binary | Summary |
| Real Plugin | `real` | `recon` | `safe` | `x` | desc. |
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(catalog_content)
        path = Path(f.name)

    try:
        result = parse_plugins_md(path)
        assert "real" in result
        assert "ID" not in result
    finally:
        path.unlink()


def test_parse_plugins_md_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        path = Path(f.name)

    try:
        result = parse_plugins_md(path)
        assert result == {}
    finally:
        path.unlink()


def test_extract_counts_from_catalog_parses_all_counts():
    catalog_content = """## At a Glance

- Total plugins: 59
- Safe plugins: 26
- Intrusive plugins: 25
- Exploit plugins: 8
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(catalog_content)
        path = Path(f.name)

    try:
        counts = extract_counts_from_catalog(path)
        assert counts["total_plugins"] == 59
        assert counts["safe_plugins"] == 26
        assert counts["intrusive_plugins"] == 25
        assert counts["exploit_plugins"] == 8
    finally:
        path.unlink()


def test_extract_counts_from_catalog_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        path = Path(f.name)

    try:
        counts = extract_counts_from_catalog(path)
        assert counts == {}
    finally:
        path.unlink()


def test_extract_category_counts_from_catalog_parses_table():
    catalog_content = """## Category Summary

| Category | Count |
| --- | ---: |
| `recon` | 17 |
| `vulnerability` | 12 |
| `web` | 5 |

## Another Section
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(catalog_content)
        path = Path(f.name)

    try:
        counts = extract_category_counts_from_catalog(path)
        assert counts["recon"] == 17
        assert counts["vulnerability"] == 12
        assert counts["web"] == 5
        assert "Category" not in counts
    finally:
        path.unlink()


def test_extract_category_counts_from_catalog_stops_at_next_header():
    catalog_content = """## Category Summary

| Category | Count |
| --- | ---: |
| `recon` | 17 |

## Next Section

| `web` | 5 |
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(catalog_content)
        path = Path(f.name)

    try:
        counts = extract_category_counts_from_catalog(path)
        assert counts["recon"] == 17
        assert "web" not in counts
    finally:
        path.unlink()


def test_validate_catalog_in_sync_returns_true():
    catalog_content = """# Title

| Plugin | ID | Category | Safety | Primary Binary | Summary |
| --- | --- | --- | --- | --- | --- |
| Test Plugin | `test_plugin` | `recon` | `safe` | `x` | desc. |

## At a Glance

- Total plugins: 1
- Safe plugins: 1
- Intrusive plugins: 0
- Exploit plugins: 0

## Category Summary

| Category | Count |
| --- | ---: |
| `recon` | 1 |
"""
    plugin_meta = '{"id": "test_plugin", "category": "recon", "safety": {"level": "safe"}}'

    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "PLUGINS.md"
        plugins_dir = Path(tmpdir) / "plugins"
        plugins_dir.mkdir()
        plugin_dir = plugins_dir / "test_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "metadata.json").write_text(plugin_meta)

        catalog_path.write_text(catalog_content)

        valid, issues = validate_catalog(catalog_path, plugins_dir)
        assert valid is True
        assert issues == []


def test_validate_catalog_missing_from_catalog_returns_false():
    catalog_content = """# Title

| Plugin | ID | Category | Safety | Primary Binary | Summary |
| --- | --- | --- | --- | --- | --- |
| Listed Plugin | `listed` | `recon` | `safe` | `x` | desc. |

## At a Glance

- Total plugins: 1
- Safe plugins: 1
- Intrusive plugins: 0
- Exploit plugins: 0

## Category Summary

| Category | Count |
| --- | ---: |
| `recon` | 1 |
"""
    plugin_meta = '{"id": "actual", "category": "recon", "safety": {"level": "safe"}}'

    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "PLUGINS.md"
        plugins_dir = Path(tmpdir) / "plugins"
        plugins_dir.mkdir()
        plugin_dir = plugins_dir / "actual"
        plugin_dir.mkdir()
        (plugin_dir / "metadata.json").write_text(plugin_meta)

        catalog_path.write_text(catalog_content)

        valid, issues = validate_catalog(catalog_path, plugins_dir)
        assert valid is False
        assert any("Missing from PLUGINS.md" in i for i in issues)


def test_validate_catalog_extra_in_catalog_returns_false():
    catalog_content = """# Title

| Plugin | ID | Category | Safety | Primary Binary | Summary |
| --- | --- | --- | --- | --- | --- |
| Extra Plugin | `extra` | `recon` | `safe` | `x` | desc. |

## At a Glance

- Total plugins: 0
- Safe plugins: 0
- Intrusive plugins: 0
- Exploit plugins: 0

## Category Summary

| Category | Count |
| --- | ---: |
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "PLUGINS.md"
        plugins_dir = Path(tmpdir) / "plugins"
        plugins_dir.mkdir()

        catalog_path.write_text(catalog_content)

        valid, issues = validate_catalog(catalog_path, plugins_dir)
        assert valid is False
        assert any("In PLUGINS.md but not in plugins/" in i for i in issues)


def test_validate_catalog_count_mismatch_returns_false():
    catalog_content = """# Title

| Plugin | ID | Category | Safety | Primary Binary | Summary |
| --- | --- | --- | --- | --- | --- |
| Test Plugin | `test` | `recon` | `safe` | `x` | desc. |

## At a Glance

- Total plugins: 99
- Safe plugins: 99
- Intrusive plugins: 0
- Exploit plugins: 0

## Category Summary

| Category | Count |
| --- | ---: |
| `recon` | 99 |
"""
    plugin_meta = '{"id": "test", "category": "recon", "safety": {"level": "safe"}}'

    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "PLUGINS.md"
        plugins_dir = Path(tmpdir) / "plugins"
        plugins_dir.mkdir()
        plugin_dir = plugins_dir / "test"
        plugin_dir.mkdir()
        (plugin_dir / "metadata.json").write_text(plugin_meta)

        catalog_path.write_text(catalog_content)

        valid, issues = validate_catalog(catalog_path, plugins_dir)
        assert valid is False
        assert any("Total plugins mismatch" in i for i in issues)
