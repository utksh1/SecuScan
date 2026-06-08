#!/usr/bin/env python3
"""
Verify or refresh checksums for specified plugin directories.

The checksum covers parser.py and metadata.json content with the
'checksum' field stripped, so updating the stored value does not
invalidate the hash.

Usage:
  python scripts/refresh_plugin_checksums.py --verify plugins/amass plugins/fuzzer
  python scripts/refresh_plugin_checksums.py --update plugins/amass plugins/fuzzer
  python scripts/refresh_plugin_checksums.py --update-all
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def compute_plugin_checksum(plugin_dir: Path) -> str:
    """
    Compute SHA-256 over parser.py and metadata.json (checksum field stripped).
    Sorting filenames ensures a stable, platform-independent order.
    """
    sha256 = hashlib.sha256()
    for filename in sorted(["metadata.json", "parser.py"]):
        filepath = plugin_dir / filename
        if not filepath.exists():
            continue
        if filename == "metadata.json":
            # Strip the checksum field so updating it doesn't change the hash
            data = json.loads(filepath.read_text(encoding="utf-8"))
            data.pop("checksum", None)
            content = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        else:
            content = filepath.read_bytes()
        sha256.update(content)
    return sha256.hexdigest()


def verify_plugins(plugin_dirs: list) -> bool:
    drift = False
    for plugin_dir in plugin_dirs:
        metadata_path = plugin_dir / "metadata.json"
        if not metadata_path.exists():
            print(f"MISSING:  {plugin_dir}/metadata.json")
            drift = True
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        stored = metadata.get("checksum", "")
        computed = compute_plugin_checksum(plugin_dir)
        if stored != computed:
            print(f"DRIFT:    {plugin_dir.name}  stored={stored[:12]}  computed={computed[:12]}")
            drift = True
        else:
            print(f"OK:       {plugin_dir.name}")
    return not drift


def update_plugins(plugin_dirs: list) -> None:
    for plugin_dir in plugin_dirs:
        metadata_path = plugin_dir / "metadata.json"
        if not metadata_path.exists():
            print(f"SKIP:     {plugin_dir} (no metadata.json)")
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        checksum = compute_plugin_checksum(plugin_dir)
        metadata["checksum"] = checksum
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        print(f"UPDATED:  {plugin_dir.name}  checksum={checksum[:12]}")


def main():
    parser = argparse.ArgumentParser(description="Plugin checksum verifier/updater")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify", nargs="+", metavar="PLUGIN_DIR",
                       help="Verify checksums for given plugin directories")
    group.add_argument("--update", nargs="+", metavar="PLUGIN_DIR",
                       help="Update checksums for given plugin directories")
    group.add_argument("--update-all", action="store_true",
                       help="Update checksums for all plugins")
    args = parser.parse_args()

    plugins_root = Path("plugins")

    if args.update_all:
        dirs = sorted(p for p in plugins_root.iterdir() if p.is_dir())
        update_plugins(dirs)
        sys.exit(0)

    if args.update:
        dirs = [Path(d) for d in args.update]
        update_plugins(dirs)
        sys.exit(0)

    if args.verify:
        dirs = [Path(d) for d in args.verify]
        ok = verify_plugins(dirs)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
