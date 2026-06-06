#!/usr/bin/env python3
"""Refresh or verify plugin checksums based on current metadata and parser files."""
import hashlib
import json
import os
import sys

PLUGINS_DIR = "plugins"
MANIFEST_FILE = os.path.join(PLUGINS_DIR, "checksums.json")


def compute_checksum(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def collect_live_checksums():
    checksums = {}
    for plugin in sorted(os.listdir(PLUGINS_DIR)):
        plugin_path = os.path.join(PLUGINS_DIR, plugin)
        if not os.path.isdir(plugin_path):
            continue
        for filename in ("metadata.json", "parser.py"):
            filepath = os.path.join(plugin_path, filename)
            if os.path.exists(filepath):
                checksums[filepath] = compute_checksum(filepath)
    return checksums


def main():
    dry_run = "--dry-run" in sys.argv

    live = collect_live_checksums()

    if not dry_run:
        with open(MANIFEST_FILE, "w") as f:
            json.dump(live, f, indent=2)
            f.write("\n")
        print(f"Updated {MANIFEST_FILE} ({len(live)} entries)")
        sys.exit(0)

    # --dry-run: verify mode — compare live against committed manifest
    if not os.path.exists(MANIFEST_FILE):
        print(f"ERROR: No manifest found at {MANIFEST_FILE}.")
        print("Run without --dry-run first to generate it.")
        sys.exit(1)

    with open(MANIFEST_FILE) as f:
        committed = json.load(f)

    drift = False

    for path, sha in committed.items():
        if path not in live:
            print(f"MISSING:  {path}")
            drift = True
        elif live[path] != sha:
            print(f"CHANGED:  {path}")
            drift = True

    for path in live:
        if path not in committed:
            print(f"EXTRA:    {path}  (not in manifest)")
            drift = True

    if drift:
        print("\nDrift detected. Run: python scripts/refresh_plugin_checksums.py")
        sys.exit(1)

    print(f"OK: all {len(live)} plugin checksums match the manifest.")
    sys.exit(0)


if __name__ == "__main__":
    main()
