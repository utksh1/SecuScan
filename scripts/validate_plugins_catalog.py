#!/usr/bin/env python3
"""
validate_plugins_catalog.py

Automated sync check between PLUGINS.md catalog and actual plugin metadata files.

This script validates that:
  1. All plugins in plugins/ have an entry in PLUGINS.md
  2. All entries in PLUGINS.md correspond to actual plugins
  3. Plugin counts match (safe, intrusive, exploit)
  4. Category counts are accurate

Usage:
  # Validate the catalog locally
  python scripts/validate_plugins_catalog.py

  # Use custom paths (useful for CI)
  python scripts/validate_plugins_catalog.py --catalog PLUGINS.md --plugins-dir plugins

Exit codes:
  0 - Catalog is in sync
  1 - Validation failed (drift detected)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set


def parse_plugins_md(catalog_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Parse PLUGINS.md and extract plugin metadata from the index table.

    Returns dict mapping plugin ID -> {"name": ..., "category": ..., "safety": ...}
    """
    if not catalog_path.exists():
        print(f"[ERROR] PLUGINS.md not found at: {catalog_path}", file=sys.stderr)
        sys.exit(1)

    catalog_text = catalog_path.read_text(encoding="utf-8")
    plugins: Dict[str, Dict[str, str]] = {}

    # Extract plugin index table using regex
    # Pattern: | Plugin Name | `plugin_id` | `category` | `safety` | ... |
    table_pattern = (
        r"\|\s*([^\|]+?)\s*\|\s*`([^`]+?)`\s*\|\s*`([^`]+?)`\s*\|\s*`([^`]+?)`"
    )

    for match in re.finditer(table_pattern, catalog_text):
        name = match.group(1).strip()
        plugin_id = match.group(2).strip()
        category = match.group(3).strip()
        safety = match.group(4).strip()

        # Skip header row
        if plugin_id == "ID" or name == "Plugin":
            continue

        plugins[plugin_id] = {
            "name": name,
            "category": category,
            "safety": safety,
        }

    return plugins


def scan_actual_plugins(plugins_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    Scan plugins/ directory and extract plugin metadata from each metadata.json.

    Returns dict mapping plugin ID -> {"id": ..., "category": ..., "safety": ...}
    """
    if not plugins_dir.exists():
        print(f"[ERROR] plugins directory not found at: {plugins_dir}", file=sys.stderr)
        sys.exit(1)

    plugins: Dict[str, Dict[str, str]] = {}

    for plugin_folder in sorted(plugins_dir.iterdir()):
        if not plugin_folder.is_dir():
            continue

        metadata_file = plugin_folder / "metadata.json"
        if not metadata_file.exists():
            print(
                f"[WARNING] No metadata.json in {plugin_folder.name}", file=sys.stderr
            )
            continue

        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            plugin_id = metadata.get("id", plugin_folder.name)
            category = metadata.get("category", "unknown")

            # FIXED: Correctly parse safety level inner object from metadata.json
            safety_block = metadata.get("safety", {})
            safety = (
                safety_block.get("level", "unknown")
                if isinstance(safety_block, dict)
                else "unknown"
            )

            plugins[plugin_id] = {
                "id": plugin_id,
                "category": category,
                "safety": safety,
                "folder": plugin_folder.name,
            }
        except json.JSONDecodeError as e:
            print(
                f"[WARNING] Invalid JSON in {plugin_folder.name}/metadata.json: {e}",
                file=sys.stderr,
            )
            continue

    return plugins


def extract_counts_from_catalog(catalog_path: Path) -> Dict[str, int]:
    """Extract At a Glance counts from PLUGINS.md."""
    counts: Dict[str, int] = {}
    catalog_text = catalog_path.read_text(encoding="utf-8")

    # Pattern: "- Total plugins: 60"
    pattern = r"-\s+(\w+[\w\s]*?):\s+(\d+)"
    for match in re.finditer(pattern, catalog_text):
        key = match.group(1).strip().lower().replace(" ", "_")
        value = int(match.group(2))
        counts[key] = value

    return counts


def extract_category_counts_from_catalog(catalog_path: Path) -> Dict[str, int]:
    """Extract category counts table from PLUGINS.md."""
    counts: Dict[str, int] = {}
    catalog_text = catalog_path.read_text(encoding="utf-8")

    # Pattern: | `category_name` | count |
    pattern = r"\|\s*`([^`]+?)`\s*\|\s*(\d+)\s*\|"
    in_category_section = False

    for line in catalog_text.split("\n"):
        if "Category Summary" in line:
            in_category_section = True
            continue
        if in_category_section and "##" in line:
            break

        if in_category_section:
            match = re.search(pattern, line)
            if match:
                category = match.group(1).strip()
                count = int(match.group(2))
                if category != "Category":  # Skip header
                    counts[category] = count

    return counts


def validate_catalog(catalog_path: Path, plugins_dir: Path) -> Tuple[bool, List[str]]:
    """
    Validate that PLUGINS.md is in sync with actual plugins.

    Returns (is_valid, list_of_issues)
    """
    issues: List[str] = []

    # Parse catalog and scan actual plugins
    catalog_plugins = parse_plugins_md(catalog_path)
    actual_plugins = scan_actual_plugins(plugins_dir)

    # Check 1: All actual plugins are in catalog
    missing_in_catalog = set(actual_plugins.keys()) - set(catalog_plugins.keys())
    if missing_in_catalog:
        issues.append(
            f"Missing from PLUGINS.md: {', '.join(sorted(missing_in_catalog))}"
        )

    # Check 2: All catalog entries correspond to actual plugins
    extra_in_catalog = set(catalog_plugins.keys()) - set(actual_plugins.keys())
    if extra_in_catalog:
        issues.append(
            f"In PLUGINS.md but not in plugins/: {', '.join(sorted(extra_in_catalog))}"
        )

    # Check 3: Total plugin count
    catalog_counts = extract_counts_from_catalog(catalog_path)
    total_plugins_expected = catalog_counts.get("total_plugins")
    if total_plugins_expected is not None:
        actual_total = len(actual_plugins)
        if actual_total != total_plugins_expected:
            issues.append(
                f"Total plugins mismatch: catalog says {total_plugins_expected}, "
                f"but found {actual_total}"
            )

    # Check 4: Safety level counts
    actual_safety_counts = {}
    for plugin in actual_plugins.values():
        safety = plugin.get("safety", "unknown")
        actual_safety_counts[safety] = actual_safety_counts.get(safety, 0) + 1

    for safety_level, count_key in [
        ("safe", "safe_plugins"),
        ("intrusive", "intrusive_plugins"),
        ("exploit", "exploit_plugins"),
    ]:
        expected = catalog_counts.get(count_key)
        actual = actual_safety_counts.get(safety_level, 0)
        if expected is not None and actual != expected:
            issues.append(
                f"Safety level '{safety_level}' count mismatch: "
                f"catalog says {expected}, but found {actual}"
            )

    # Check 5: Category counts
    catalog_category_counts = extract_category_counts_from_catalog(catalog_path)
    actual_category_counts = {}
    for plugin in actual_plugins.values():
        category = plugin.get("category", "unknown")
        actual_category_counts[category] = actual_category_counts.get(category, 0) + 1

    for category, expected_count in catalog_category_counts.items():
        actual_count = actual_category_counts.get(category, 0)
        if actual_count != expected_count:
            issues.append(
                f"Category '{category}' count mismatch: "
                f"catalog says {expected_count}, but found {actual_count}"
            )

    return (len(issues) == 0, issues)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate that PLUGINS.md is in sync with plugin metadata files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_plugins_catalog.py
  python scripts/validate_plugins_catalog.py --catalog ./PLUGINS.md --plugins-dir ./plugins
        """,
    )

    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("PLUGINS.md"),
        help="Path to PLUGINS.md (default: PLUGINS.md)",
    )
    parser.add_argument(
        "--plugins-dir",
        type=Path,
        default=Path("plugins"),
        help="Path to plugins directory (default: plugins)",
    )

    args = parser.parse_args()

    # Ensure paths are absolute for consistent error messages
    catalog_path = args.catalog.resolve()
    plugins_path = args.plugins_dir.resolve()

    print(f"Validating plugin catalog...")
    print(f"  Catalog: {catalog_path}")
    print(f"  Plugins: {plugins_path}")
    print()

    is_valid, issues = validate_catalog(catalog_path, plugins_path)

    if is_valid:
        print("[✓] Catalog is in sync!")
        sys.exit(0)
    else:
        print("[✗] Catalog validation failed:")
        print()
        print(
            f"DEBUG - Actual plugins found in folder: {sorted(list(scan_actual_plugins(plugins_path).keys()))}\n"
        )
        for issue in issues:
            print(f"  • {issue}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
