#!/usr/bin/env python3
"""
validate_plugins.py — SecuScan pre-PR plugin metadata validator

Usage:
    # Validate all plugins
    python scripts/validate_plugins.py

    # Validate a single plugin by directory name / plugin id
    python scripts/validate_plugins.py --plugin nmap

    # Point at a custom plugins directory
    python scripts/validate_plugins.py --plugins-dir path/to/plugins

    # Machine-readable JSON output
    python scripts/validate_plugins.py --json

Exit codes:
    0  — all plugins are valid
    1  — one or more plugins have validation errors
    2  — usage / configuration error (directory not found, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import (
    validate_all_plugins,
    validate_one_plugin,
    ValidationResult,
)

DEFAULT_PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _print_result(result: ValidationResult) -> None:
    status = "✓ PASS" if result.valid else "✗ FAIL"
    print(f"  {status}  {result.plugin_id}  ({result.plugin_dir.name})")
    for err in result.errors:
        print(err.display())


def _results_to_dict(results: list[ValidationResult]) -> dict:
    return {
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.valid),
            "failed": sum(1 for r in results if not r.valid),
        },
        "plugins": [
            {
                "id": r.plugin_id,
                "dir": str(r.plugin_dir),
                "valid": r.valid,
                "errors": [{"path": e.path, "message": e.message} for e in r.errors],
            }
            for r in results
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="validate_plugins",
        description="Validate SecuScan plugin metadata before opening a pull request.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--plugin",
        metavar="ID",
        help="Validate only this plugin (directory name or plugin id).",
    )
    p.add_argument(
        "--plugins-dir",
        metavar="DIR",
        default=str(DEFAULT_PLUGINS_DIR),
        help=f"Path to the plugins directory (default: {DEFAULT_PLUGINS_DIR}).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable output.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    plugins_dir = Path(args.plugins_dir)

    # ---- single plugin ------------------------------------------------
    if args.plugin:
        plugin_dir = plugins_dir / args.plugin
        if not plugin_dir.exists():
            print(f"ERROR: Plugin directory not found: {plugin_dir}", file=sys.stderr)
            return 2

        result = validate_one_plugin(plugin_dir)
        results = [result]

    # ---- all plugins --------------------------------------------------
    else:
        if not plugins_dir.exists():
            print(f"ERROR: Plugins directory not found: {plugins_dir}", file=sys.stderr)
            return 2

        try:
            results = validate_all_plugins(plugins_dir)
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    # ---- output -------------------------------------------------------
    if args.json:
        print(json.dumps(_results_to_dict(results), indent=2))
    else:
        total = len(results)
        failed = [r for r in results if not r.valid]
        passed = total - len(failed)

        print(f"\nSecuScan Plugin Validator — {total} plugin(s) checked\n")
        print("─" * 60)
        for r in results:
            _print_result(r)
        print("─" * 60)

        if failed:
            print(
                f"\n✗ {len(failed)} plugin(s) failed validation, " f"{passed} passed.\n"
            )
            print("Fix the errors above, then re-run:")
            print("  python scripts/validate_plugins.py\n")
        else:
            print(f"\n✓ All {total} plugin(s) are valid.\n")

    any_failed = any(not r.valid for r in results)
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
