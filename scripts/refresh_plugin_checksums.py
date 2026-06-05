#!/usr/bin/env python3
"""Refresh plugin checksums based on current metadata and parser files."""

import hashlib
import os
import sys

PLUGINS_DIR = "plugins"
CHECKSUM_FILE = os.path.join(PLUGINS_DIR, "checksums.txt")

def compute_checksum(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def main():
    dry_run = "--dry-run" in sys.argv
    
    checksums = {}
    for plugin in os.listdir(PLUGINS_DIR):
        plugin_path = os.path.join(PLUGINS_DIR, plugin)
        if not os.path.isdir(plugin_path):
            continue
            
        metadata = os.path.join(plugin_path, "metadata.json")
        if os.path.exists(metadata):
            checksums[metadata] = compute_checksum(metadata)
        
        parser = os.path.join(plugin_path, "parser.py")
        if os.path.exists(parser):
            checksums[parser] = compute_checksum(parser)
    
    if dry_run:
        print("Checksums that would be written:")
        for path, cs in checksums.items():
            print(f"{cs}  {path}")
    else:
        with open(CHECKSUM_FILE, "w") as f:
            for path, cs in checksums.items():
                f.write(f"{cs}  {path}\n")
        print(f"Updated {CHECKSUM_FILE}")

if __name__ == "__main__":
    main()
