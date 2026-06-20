#!/usr/bin/env python3
"""
refresh_plugin_checksum.py

A helper script for contributors and maintainers to recalculate plugin
checksums after editing metadata.json or parser.py.

Why this exists:
    Plugin metadata files include integrity checksums. If you edit a plugin's
    metadata or parser without refreshing the checksum, the backend will reject
    the plugin during load and unrelated backend tests will fail.

Usage:
    # Refresh a single plugin by its folder name (plugin id)
    python scripts/refresh_plugin_checksum.py --plugin nmap

    # Refresh all plugins at once
    python scripts/refresh_plugin_checksum.py --all

    # Dry run — show what would change without writing anything
    python scripts/refresh_plugin_checksum.py --all --dry-run

    # Use a custom plugins directory
    python scripts/refresh_plugin_checksum.py --all --plugins-dir /path/to/plugins
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path


# ── Digest logic (mirrors PluginManager.compute_plugin_digest exactly) ────────


def compute_plugin_digest(metadata_file: Path, parser_file: Path) -> str:
    """
    Compute deterministic plugin digest ignoring mutable checksum/signature fields.
    This is the same logic as PluginManager.compute_plugin_digest in the backend
    so the script and backend always agree on the checksum value.
    """
    # Load metadata and strip the mutable fields before hashing
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    metadata.pop("checksum", None)
    metadata.pop("signature", None)

    # Canonical JSON — sorted keys, no extra whitespace
    metadata_canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    metadata_digest = hashlib.sha256(metadata_canonical.encode("utf-8")).hexdigest()

    # Hash parser.py if it exists, otherwise use empty string
    parser_digest = ""
    if parser_file.exists():
        parser_bytes = parser_file.read_bytes()
        parser_bytes_normalized = parser_bytes.replace(b"\r\n", b"\n")
        parser_digest = hashlib.sha256(parser_bytes_normalized).hexdigest()

    # Final digest combines both
    return hashlib.sha256(
        f"{metadata_digest}:{parser_digest}".encode("utf-8")
    ).hexdigest()


# ── Core refresh logic ────────────────────────────────────────────────────────


def refresh_plugin(plugin_dir: Path, dry_run: bool = False) -> bool:
    """
    Recalculate and write the checksum for a single plugin.

    Args:
        plugin_dir: Path to the plugin folder (e.g. plugins/nmap)
        dry_run:    If True, print what would change but don't write anything

    Returns:
        True if the plugin was processed successfully, False on error
    """
    metadata_file = plugin_dir / "metadata.json"
    parser_file = plugin_dir / "parser.py"

    # Validate plugin folder structure
    if not plugin_dir.exists():
        print(f"  [ERROR] Plugin directory not found: {plugin_dir}", file=sys.stderr)
        return False

    if not metadata_file.exists():
        print(f"  [ERROR] metadata.json not found in: {plugin_dir}", file=sys.stderr)
        return False

    # Compute the new checksum
    try:
        new_checksum = compute_plugin_digest(metadata_file, parser_file)
    except Exception as e:
        print(
            f"  [ERROR] Failed to compute digest for {plugin_dir.name}: {e}",
            file=sys.stderr,
        )
        return False

    # Read current metadata
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(
            f"  [ERROR] Invalid JSON in metadata.json for {plugin_dir.name}: {e}",
            file=sys.stderr,
        )
        return False

    old_checksum = metadata.get("checksum", "<none>")

    # Check if update is needed
    if old_checksum == new_checksum:
        print(f"  [OK]    {plugin_dir.name} — checksum already up to date")
        return True

    print(f"  [UPDATE] {plugin_dir.name}")
    print(f"           old: {old_checksum}")
    print(f"           new: {new_checksum}")

    if dry_run:
        print(f"           (dry run — not written)")
        return True

    # Write the updated checksum back into metadata.json
    metadata["checksum"] = new_checksum
    metadata_file.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"           checksum updated successfully")
    return True


def refresh_all_plugins(plugins_dir: Path, dry_run: bool = False) -> None:
    """Refresh checksums for every plugin found in plugins_dir."""
    if not plugins_dir.exists():
        print(f"[ERROR] Plugins directory not found: {plugins_dir}", file=sys.stderr)
        sys.exit(1)

    plugin_dirs = sorted([d for d in plugins_dir.iterdir() if d.is_dir()])

    if not plugin_dirs:
        print(f"[WARNING] No plugin folders found in: {plugins_dir}")
        return

    print(f"Refreshing checksums for {len(plugin_dirs)} plugins...\n")

    success_count = 0
    error_count = 0

    for plugin_dir in plugin_dirs:
        if refresh_plugin(plugin_dir, dry_run=dry_run):
            success_count += 1
        else:
            error_count += 1

    print(f"\nDone — {success_count} succeeded, {error_count} failed.")

    if error_count > 0:
        sys.exit(1)


# ── CLI entry point ───────────────────────────────────────────────────────────


def main() -> None:
    # Default plugins dir is relative to this script's location
    # scripts/ is one level below the project root, plugins/ is at project root
    default_plugins_dir = Path(__file__).parent.parent / "plugins"

    parser = argparse.ArgumentParser(
        description="Refresh plugin checksums after editing metadata or parser files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/refresh_plugin_checksum.py --plugin nmap
  python scripts/refresh_plugin_checksum.py --all
  python scripts/refresh_plugin_checksum.py --all --dry-run
  python scripts/refresh_plugin_checksum.py --plugin nmap --plugins-dir /custom/path
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--plugin",
        metavar="PLUGIN_ID",
        help="Refresh a single plugin by its folder name (e.g. nmap, whois_lookup)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Refresh checksums for all plugins in the plugins directory",
    )

    parser.add_argument(
        "--plugins-dir",
        metavar="PATH",
        type=Path,
        default=default_plugins_dir,
        help=f"Path to plugins directory (default: {default_plugins_dir})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing anything",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN] No files will be modified.\n")

    if args.all:
        refresh_all_plugins(args.plugins_dir, dry_run=args.dry_run)
    else:
        plugin_dir = args.plugins_dir / args.plugin
        print(f"Refreshing checksum for plugin: {args.plugin}\n")
        success = refresh_plugin(plugin_dir, dry_run=args.dry_run)
        if not success:
            sys.exit(1)
        print("\nDone.")


if __name__ == "__main__":
    main()
