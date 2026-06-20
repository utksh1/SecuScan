#!/usr/bin/env python3
"""
Generate Software Bill of Materials (SBOM) in CycloneDX 1.4 format.

Usage:
    python scripts/generate_sbom.py --output sbom.json
"""

import json
import subprocess
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


def get_python_packages(requirements_file: str) -> List[Dict[str, str]]:
    """Extract Python packages from requirements and resolve their installed versions"""
    req_path = Path(requirements_file)
    if not req_path.exists():
        return []

    req_names = set()
    with open(req_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Extract package name
            parts = re.split(r"==|>=|<=|>|<|;|@", line)
            if parts:
                name = parts[0].strip().lower().replace("_", "-")
                if name:
                    req_names.add(name)

    packages = []
    try:
        # Get pip list JSON
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        pip_packages = json.loads(result.stdout)
        for pkg in pip_packages:
            pkg_name = pkg["name"].lower().replace("_", "-")
            if pkg_name in req_names:
                packages.append(
                    {
                        "name": pkg["name"],
                        "version": pkg["version"],
                        "type": "python-package",
                        "scope": "runtime"
                        if "dev" not in requirements_file
                        else "development",
                    }
                )
    except Exception as e:
        print(f"Warning: Failed to query pip list: {e}", file=sys.stderr)

    return packages


def get_npm_packages(package_json_file: str) -> List[Dict[str, str]]:
    """Extract npm packages from package.json and resolve versions using npm ls"""
    packages = []
    package_json_path = Path(package_json_file)
    if not package_json_path.exists():
        return []

    # Get npm list JSON
    try:
        result = subprocess.run(
            ["npm", "ls", "--json", "--depth=0"],
            capture_output=True,
            text=True,
            cwd=str(package_json_path.parent),
        )
        npm_data = json.loads(result.stdout)
        deps = npm_data.get("dependencies", {})
        for name, data in deps.items():
            if isinstance(data, dict):
                version = data.get("version") or "unknown"
                packages.append(
                    {
                        "name": name,
                        "version": version,
                        "type": "npm-package",
                        "scope": "development" if data.get("dev") else "runtime",
                    }
                )
    except Exception as e:
        # Fallback to parsing package.json direct dependencies
        try:
            with open(package_json_path) as f:
                pdata = json.load(f)
            for name, ver in pdata.get("dependencies", {}).items():
                packages.append(
                    {
                        "name": name,
                        "version": ver.replace("^", "").replace("~", ""),
                        "type": "npm-package",
                        "scope": "runtime",
                    }
                )
            for name, ver in pdata.get("devDependencies", {}).items():
                packages.append(
                    {
                        "name": name,
                        "version": ver.replace("^", "").replace("~", ""),
                        "type": "npm-package",
                        "scope": "development",
                    }
                )
        except Exception:
            pass

    return packages


def generate_sbom(output_file: str, include_dev: bool = False) -> None:
    """Generate SBOM in CycloneDX 1.4 format"""

    # Collect packages
    packages: List[Dict[str, Any]] = []

    # Add Python packages
    try:
        packages.extend(get_python_packages("backend/requirements.txt"))
        if include_dev:
            packages.extend(get_python_packages("backend/requirements-dev.txt"))
    except Exception as e:
        print(f"Warning: Failed to extract Python packages: {e}", file=sys.stderr)

    # Add npm packages
    try:
        packages.extend(get_npm_packages("frontend/package.json"))
    except Exception as e:
        print(f"Warning: Failed to extract npm packages: {e}", file=sys.stderr)

    # Build CycloneDX SBOM
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:secuscan-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "component": {
                "bom-ref": "secuscan",
                "type": "application",
                "name": "SecuScan",
                "description": "Integrated security scanning platform",
            },
        },
        "components": [
            {
                "bom-ref": f"{pkg['name']}-{pkg['version']}",
                "type": pkg["type"].split("-")[0],
                "name": pkg["name"],
                "version": pkg["version"],
                "scope": pkg.get("scope", "required"),
            }
            for pkg in packages
        ],
    }

    # Ensure parent directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(sbom, f, indent=2)

    print(f"[OK] SBOM written to {output_file}")
    print(f"  Total components: {len(sbom['components'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Software Bill of Materials")
    parser.add_argument("--output", default="sbom.json", help="Output file")
    parser.add_argument(
        "--include-dev", action="store_true", help="Include dev dependencies"
    )

    args = parser.parse_args()
    generate_sbom(args.output, include_dev=args.include_dev)
