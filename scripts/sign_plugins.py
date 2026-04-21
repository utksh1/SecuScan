"""Generate plugin checksums and optional HMAC signatures for metadata files."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.secuscan.plugins import PluginManager


def sign_plugins(plugins_dir: Path, signature_key: str | None) -> int:
    updated = 0
    for metadata_file in sorted(plugins_dir.glob("*/metadata.json")):
        parser_file = metadata_file.parent / "parser.py"
        data = json.loads(metadata_file.read_text(encoding="utf-8"))

        digest = PluginManager.compute_plugin_digest(metadata_file, parser_file)
        data["checksum"] = digest

        if signature_key:
            data["signature"] = hmac.new(
                signature_key.encode("utf-8"),
                digest.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        elif "signature" in data:
            data.pop("signature", None)

        metadata_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        updated += 1
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugins-dir", default="plugins", help="Plugins directory")
    parser.add_argument("--signature-key", default=None, help="Optional HMAC signing key")
    args = parser.parse_args()

    count = sign_plugins(Path(args.plugins_dir), args.signature_key)
    print(f"Updated {count} plugin metadata files")


if __name__ == "__main__":
    main()
