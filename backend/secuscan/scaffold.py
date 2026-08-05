import json
import re
import sys
from pathlib import Path
from typing import Optional

from backend.secuscan.config import settings
from backend.secuscan.plugins import PluginManager


def prompt_input(prompt_text: str, default: Optional[str] = None) -> str:
    """Prompt the user for input with an optional default value."""
    try:
        val = input(prompt_text).strip()
        if not val and default is not None:
            return default
        return val
    except (KeyboardInterrupt, EOFError):
        print("\n[!] Scaffolding cancelled.")
        sys.exit(1)


def generate_scaffold(
    plugin_id: Optional[str] = None,
    name: Optional[str] = None,
    safety: Optional[str] = None,
) -> None:
    """Generate a new plugin directory, metadata, and parser stub."""
    print("=== SecuScan Plugin Scaffolding ===")

    # 1. Interactive Inputs & Fallbacks
    if plugin_id is None:
        while True:
            plugin_id = prompt_input("Plugin ID (e.g. my_scanner): ").lower()
            if not plugin_id:
                print("[-] Plugin ID cannot be empty.")
                continue
            if not re.match(r"^[a-z0-9_-]+$", plugin_id):
                print("[-] Plugin ID must contain only lowercase letters, numbers, underscores, or hyphens.")
                continue
            break
    else:
        plugin_id = plugin_id.lower()
        if not plugin_id:
            print("[-] Error: Plugin ID cannot be empty.")
            sys.exit(1)
        if not re.match(r"^[a-z0-9_-]+$", plugin_id):
            print("[-] Error: Plugin ID must contain only lowercase letters, numbers, underscores, or hyphens.")
            sys.exit(1)

    if not name:
        name = prompt_input(f"Plugin Display Name [{plugin_id}]: ", default=plugin_id)

    if not safety:
        while True:
            safety = prompt_input("Safety Level (safe/intrusive/exploit) [safe]: ", default="safe").lower()
            if safety not in ["safe", "intrusive", "exploit"]:
                print("[-] Invalid safety level. Choose from: safe, intrusive, exploit.")
                continue
            break
    else:
        safety = safety.lower()
        if safety not in ["safe", "intrusive", "exploit"]:
            print(f"[-] Error: Invalid safety level '{safety}'. Must be 'safe', 'intrusive', or 'exploit'.")
            sys.exit(1)

    # 2. Check Existing Plugin & Enforce Path Containment
    plugins_dir = Path(settings.plugins_dir).resolve()
    target_dir = (plugins_dir / plugin_id).resolve()

    try:
        target_dir.relative_to(plugins_dir)
        if target_dir == plugins_dir:
            raise ValueError()
    except (ValueError, RuntimeError):
        print(f"[-] Error: Target directory must be inside {plugins_dir}")
        sys.exit(1)

    if target_dir.exists():
        print(f"[-] Error: Plugin directory already exists at: {target_dir}")
        sys.exit(1)

    # 3. Create Plugin Template Structures
    metadata_template = {
        "id": plugin_id,
        "name": name,
        "version": "1.0.0",
        "description": f"SecuScan plugin for {name}.",
        "long_description": f"SecuScan plugin for {name}.",
        "category": "recon",
        "author": {
            "name": "SecuScan Contributors",
            "email": "dev@secuscan.local"
        },
        "license": "MIT",
        "icon": "🔧",
        "engine": {
            "type": "cli",
            "binary": plugin_id
        },
        "command_template": [
            plugin_id,
            "{target}"
        ],
        "fields": [
            {
                "id": "target",
                "label": "Target",
                "type": "string",
                "required": True,
                "placeholder": "example.com"
            }
        ],
        "presets": {
            "default": {}
        },
        "output": {
            "format": "text",
            "parser": "custom"
        },
        "safety": {
            "level": safety,
            "requires_consent": False,
            "rate_limit": {
                "max_per_hour": 20,
                "max_concurrent": 1
            }
        },
        "dependencies": {
            "binaries": [
                plugin_id
            ],
            "python_packages": [],
            "system_packages": []
        },
        "capabilities": [
            "network"
        ]
    }

    parser_template = '''from typing import Any, Dict, List


def parse(output: str) -> Dict[str, Any]:
    """Normalize tool execution output."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    findings: List[Dict[str, Any]] = []

    for line in lines[:200]:
        findings.append({
            "title": "Observation",
            "category": "Recon",
            "severity": "info",
            "description": line,
            "remediation": "Review output details.",
            "metadata": {"raw_line": line},
        })

    return {
        "findings": findings,
        "count": len(findings),
        "items": lines[:200],
    }


def parse_output(output: str) -> Dict[str, Any]:
    """Standard parser function entry point."""
    return parse(output)
'''


    # 4. Write Files to Disk (Temporary without checksum)
    target_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = (target_dir / "metadata.json").resolve()
    parser_file = (target_dir / "parser.py").resolve()

    try:
        metadata_file.relative_to(target_dir)
        parser_file.relative_to(target_dir)
    except (ValueError, RuntimeError):
        print("[-] Error: Write target escaped containment.")
        sys.exit(1)

    # Write initial files with LF line endings to avoid line ending/checksum issues
    metadata_file.write_text(json.dumps(metadata_template, indent=2), encoding="utf-8", newline="\n")
    parser_file.write_text(parser_template, encoding="utf-8", newline="\n")

    # 5. Compute Checksum
    try:
        checksum = PluginManager.compute_plugin_digest(metadata_file, parser_file, require_parser=True)
        metadata_template["checksum"] = checksum
        # Rewrite metadata.json with the checksum
        metadata_file.write_text(json.dumps(metadata_template, indent=2), encoding="utf-8", newline="\n")
    except Exception as e:
        print(f"[-] Error: Failed to compute plugin checksum: {e}")
        # Clean up
        if metadata_file.exists():
            metadata_file.unlink()
        if parser_file.exists():
            parser_file.unlink()
        target_dir.rmdir()
        sys.exit(1)

    print(f"[+] Successfully scaffolded plugin '{plugin_id}' at: {target_dir}")
    print(f"    - Created: metadata.json (checksum: {checksum})")
    print("    - Created: parser.py")
