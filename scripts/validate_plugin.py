#!/usr/bin/env python3
"""
validate_plugin.py

Validate a single plugin without loading all plugins.

Checks:
- Metadata JSON is valid and matches the PluginMetadata schema.
- Required fields like engine.type and safety.level are present and valid.
- Checksum matches the computed digest.
- Custom parser imports cleanly and exposes a parse() function.

Usage:
  python scripts/validate_plugin.py --plugin nmap
  python scripts/validate_plugin.py --plugin plugins/nmap
  python scripts/validate_plugin.py --plugin /abs/path/to/plugins/nmap
  python scripts/validate_plugin.py --plugin nmap --plugins-dir /custom/plugins
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.secuscan.models import PluginMetadata
from backend.secuscan.plugins import PluginManager


ALLOWED_ENGINE_TYPES = {"cli", "python", "docker"}
ALLOWED_SAFETY_LEVELS = {"safe", "intrusive", "exploit"}


def resolve_plugin_dir(plugin_arg: str, plugins_dir: Path) -> Path:
    candidate = Path(plugin_arg)
    if candidate.exists():
        if candidate.is_file() and candidate.name == "metadata.json":
            return candidate.parent
        if candidate.is_dir():
            return candidate
    return plugins_dir / plugin_arg


def _import_parser(parser_file: Path, plugin_id: str) -> Optional[str]:
    try:
        spec = importlib.util.spec_from_file_location(f"parser_{plugin_id}", parser_file)
        if spec is None or spec.loader is None:
            return f"Unable to load parser module from {parser_file}"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:
        return f"Failed to import parser.py for {plugin_id}: {exc}"

    if not hasattr(module, "parse"):
        return f"parser.py for {plugin_id} is missing a parse() function"

    return None


def _compute_normalized_digest(metadata: dict, parser_file: Path) -> str:
    metadata_payload = dict(metadata)
    metadata_payload.pop("checksum", None)
    metadata_payload.pop("signature", None)
    metadata_canonical = json.dumps(metadata_payload, sort_keys=True, separators=(",", ":"))
    metadata_digest = hashlib.sha256(metadata_canonical.encode("utf-8")).hexdigest()

    if parser_file.exists():
        parser_text = parser_file.read_text(encoding="utf-8")
        parser_text = parser_text.replace("\r\n", "\n")
        parser_digest = hashlib.sha256(parser_text.encode("utf-8")).hexdigest()
    else:
        parser_digest = ""

    return hashlib.sha256(f"{metadata_digest}:{parser_digest}".encode("utf-8")).hexdigest()


def validate_plugin(plugin_dir: Path) -> bool:
    errors: List[str] = []

    metadata_file = plugin_dir / "metadata.json"
    parser_file = plugin_dir / "parser.py"

    if not plugin_dir.exists():
        errors.append(f"Plugin directory not found: {plugin_dir}")
    if not metadata_file.exists():
        errors.append(f"metadata.json not found in {plugin_dir}")

    if errors:
        for message in errors:
            print(f"[ERROR] {message}", file=sys.stderr)
        return False

    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON in {metadata_file}: {exc}", file=sys.stderr)
        return False

    try:
        plugin = PluginMetadata(**metadata)
    except ValidationError as exc:
        print("[ERROR] Metadata schema validation failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return False

    plugin_id = plugin.id or plugin_dir.name

    engine_type = plugin.engine.get("type")
    if engine_type not in ALLOWED_ENGINE_TYPES:
        errors.append(
            f"Invalid engine.type for {plugin_id}: {engine_type} (expected one of {sorted(ALLOWED_ENGINE_TYPES)})"
        )

    safety_level = plugin.safety.get("level")
    if safety_level not in ALLOWED_SAFETY_LEVELS:
        errors.append(
            f"Invalid safety.level for {plugin_id}: {safety_level} (expected one of {sorted(ALLOWED_SAFETY_LEVELS)})"
        )

    checksum = metadata.get("checksum")
    if not checksum:
        errors.append(f"Missing checksum in metadata.json for {plugin_id}")
    else:
        try:
            expected = PluginManager.compute_plugin_digest(metadata_file, parser_file)
        except Exception as exc:
            errors.append(f"Failed to compute checksum for {plugin_id}: {exc}")
        else:
            if checksum != expected:
                normalized_expected = None
                if parser_file.exists():
                    try:
                        normalized_expected = _compute_normalized_digest(metadata, parser_file)
                    except Exception:
                        normalized_expected = None

                if normalized_expected and checksum == normalized_expected:
                    print(
                        f"[WARNING] {plugin_id} parser.py uses CRLF line endings; checksum matches LF-normalized content.",
                        file=sys.stderr,
                    )
                else:
                    errors.append(
                        f"Checksum mismatch for {plugin_id}: expected {expected}, found {checksum}"
                    )

    parser_type = plugin.output.get("parser")
    if parser_type == "custom" or parser_file.exists():
        if not parser_file.exists():
            errors.append(f"Custom parser specified but parser.py not found for {plugin_id}")
        else:
            parser_error = _import_parser(parser_file, plugin_id)
            if parser_error:
                errors.append(parser_error)

    if errors:
        for message in errors:
            print(f"[ERROR] {message}", file=sys.stderr)
        return False

    print(f"[OK] {plugin_id} validated successfully")
    return True


def main() -> None:
    default_plugins_dir = ROOT / "plugins"

    parser = argparse.ArgumentParser(
        description="Validate a single plugin without loading all plugins.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_plugin.py --plugin nmap
  python scripts/validate_plugin.py --plugin plugins/nmap
  python scripts/validate_plugin.py --plugin /abs/path/to/plugins/nmap
  python scripts/validate_plugin.py --plugin nmap --plugins-dir /custom/plugins
        """,
    )
    parser.add_argument(
        "--plugin",
        required=True,
        help="Plugin id (folder name) or path to the plugin directory",
    )
    parser.add_argument(
        "--plugins-dir",
        type=Path,
        default=default_plugins_dir,
        help=f"Plugins directory when using an id (default: {default_plugins_dir})",
    )

    args = parser.parse_args()
    plugin_dir = resolve_plugin_dir(args.plugin, args.plugins_dir)

    success = validate_plugin(plugin_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
