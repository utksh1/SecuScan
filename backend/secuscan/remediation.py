"""
Dependency graph resolution and remediation conflict validation.
"""

import json
import re
import importlib.metadata
from pathlib import Path
from typing import Dict, List, Any, Tuple
from packaging.version import Version
from packaging.specifiers import SpecifierSet


def normalize_package_name(name: str) -> str:
    """Normalize a package name to lowercase with PEP 503 compatibility."""
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def clean_version_string(ver_str: str) -> str:
    """Extract numeric prefix from version strings for comparison."""
    ver_str = ver_str.strip().lower()
    if ver_str.startswith("v"):
        ver_str = ver_str[1:]
    # Match the first sequence of digits and dots (e.g., "1.2.3" in "1.2.3-ubuntu")
    match = re.match(r"^([0-9]+(?:\.[0-9]+)*)", ver_str)
    if match:
        return match.group(1)
    return ver_str


def parse_remediation_suggestion(remediation_str: str) -> Tuple[str, str] | None:
    """Parse recommendation string to extract package name and target upgrade version.

    Example: "Update framer-motion to version 11.0.0" -> ("framer-motion", "11.0.0")
    """
    pattern = r"(?:update|upgrade)\s+([a-zA-Z0-9_\-\.]+)\s+(?:to\s+)?(?:version\s+)?([a-zA-Z0-9_\-\.\+\~]+)"
    match = re.search(pattern, remediation_str, re.IGNORECASE)
    if match:
        pkg_name = normalize_package_name(match.group(1))
        version = match.group(2)
        return pkg_name, version
    return None


def handle_caret(ver_str: str) -> List[str]:
    """Convert NPM caret specification to PEP 440 constraints.

    ^1.2.3 -> >=1.2.3, <2.0.0
    ^0.2.3 -> >=0.2.3, <0.3.0
    ^0.0.3 -> >=0.0.3, <0.0.4
    """
    parts = ver_str.split(".")
    while len(parts) < 3:
        parts.append("0")

    major = "".join(filter(str.isdigit, parts[0])) or "0"
    minor = "".join(filter(str.isdigit, parts[1])) or "0"
    patch = "".join(filter(str.isdigit, parts[2])) or "0"

    if major != "0":
        next_major = int(major) + 1
        return [f">={ver_str}", f"<{next_major}.0.0"]
    elif minor != "0":
        next_minor = int(minor) + 1
        return [f">={ver_str}", f"<0.{next_minor}.0"]
    else:
        next_patch = int(patch) + 1
        return [f">={ver_str}", f"<0.0.{next_patch}"]


def handle_tilde(ver_str: str) -> List[str]:
    """Convert NPM tilde specification to PEP 440 constraints.

    ~1.2.3 -> >=1.2.3, <1.3.0
    ~1.2   -> >=1.2.0, <1.3.0
    """
    parts = ver_str.split(".")
    while len(parts) < 2:
        parts.append("0")
    major = "".join(filter(str.isdigit, parts[0])) or "0"
    minor = "".join(filter(str.isdigit, parts[1])) or "0"
    next_minor = int(minor) + 1
    return [f">={ver_str}", f"<{major}.{next_minor}.0"]


def handle_wildcard(part: str) -> List[str]:
    """Convert wildcard version strings (e.g. 1.x or 1.*) to PEP 440 constraints."""
    part = part.replace("*", "x")
    parts = part.split(".")
    if len(parts) == 1 or parts[0] == "x":
        return []
    if len(parts) == 2 or parts[1] == "x":
        major = "".join(filter(str.isdigit, parts[0])) or "0"
        next_major = int(major) + 1
        return [f">={major}.0.0", f"<{next_major}.0.0"]
    if parts[2] == "x":
        major = "".join(filter(str.isdigit, parts[0])) or "0"
        minor = "".join(filter(str.isdigit, parts[1])) or "0"
        next_minor = int(minor) + 1
        return [f">={major}.{minor}.0", f"<{major}.{next_minor}.0"]
    return []


def semver_to_pep440(semver_str: str) -> SpecifierSet:
    """Convert NPM/semver package version specifier into PEP 440 SpecifierSet."""
    semver_str = semver_str.strip()
    if not semver_str or semver_str in ("*", "x", "any"):
        return SpecifierSet()

    parts = semver_str.split()
    pep440_parts = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith("^"):
            pep440_parts.extend(handle_caret(part[1:]))
        elif part.startswith("~"):
            pep440_parts.extend(handle_tilde(part[1:]))
        elif "x" in part or "*" in part:
            pep440_parts.extend(handle_wildcard(part))
        elif part.startswith((">=", "<=", ">", "<", "==")):
            match = re.match(r"^(>=|<=|>|<|==)\s*([0-9a-zA-Z\.\-\+]+)$", part)
            if match:
                op, ver = match.groups()
                pep440_parts.append(f"{op}{ver}")
        else:
            if re.match(r"^[0-9]+(?:\.[0-9]+)?$", part):
                pep440_parts.extend(handle_wildcard(part + ".x"))
            elif re.match(r"^[0-9a-zA-Z\.\-\+]+$", part):
                pep440_parts.append(f"=={part}")

    try:
        return SpecifierSet(",".join(pep440_parts))
    except Exception:
        return SpecifierSet()


def parse_package_lock(filepath: str) -> Dict[str, List[Tuple[str, str]]]:
    """Parse a package-lock.json and extract direct and transitive package dependency requirements."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    relations = {}

    # Check for packages key (modern NPM lockfile v2/v3)
    packages = data.get("packages", {})
    for path, info in packages.items():
        if not path:
            parent = "root"
        else:
            parent = path.replace("node_modules/", "")

        deps = info.get("dependencies", {})
        peer_deps = info.get("peerDependencies", {})
        all_deps = {**deps, **peer_deps}

        if all_deps:
            relations[parent] = [(normalize_package_name(k), v) for k, v in all_deps.items()]

    # Fallback to dependencies key (NPM lockfile v1)
    dependencies = data.get("dependencies", {})
    def parse_v1_deps(deps_dict):
        for name, info in deps_dict.items():
            requires = info.get("requires", {})
            if requires:
                relations[name] = [(normalize_package_name(k), v) for k, v in requires.items()]
            child_deps = info.get("dependencies", {})
            if child_deps:
                parse_v1_deps(child_deps)

    if not packages and dependencies:
        parse_v1_deps(dependencies)

    return relations


def parse_package_json(filepath: str) -> Dict[str, List[Tuple[str, str]]]:
    """Parse a package.json for direct project dependencies."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        peer_deps = data.get("peerDependencies", {})
        all_deps = {**deps, **dev_deps, **peer_deps}
        return {
            "root": [(normalize_package_name(k), v) for k, v in all_deps.items()]
        }
    except Exception:
        return {}


def parse_requirement_line(line: str) -> Tuple[str, SpecifierSet] | None:
    """Parse a single requirements.txt line into a normalized package name and SpecifierSet."""
    line = line.strip()
    if not line or line.startswith(('#', '-')):
        return None
    # Strip environment markers (e.g. "pydantic; python_version >= '3.8'")
    line = line.split(";")[0].strip()
    match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*(.*)$", line)
    if not match:
        return None
    name, spec_str = match.groups()
    # Normalize comparison operators if present
    spec_str = spec_str.strip()
    name = normalize_package_name(name)
    try:
        spec = SpecifierSet(spec_str)
    except Exception:
        spec = SpecifierSet()
    return name, spec

def get_python_transitive_dependencies(package_name: str) -> List[Tuple[str, SpecifierSet]]:
    """Retrieve python transitive dependencies from installed metadata."""
    try:
        reqs = importlib.metadata.requires(package_name)
        if not reqs:
            return []
        dependencies = []
        for req in reqs:
            req_clean = req.split(";")[0].strip()
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*\((.*)\)$", req_clean)
            if match:
                dep_name, dep_spec = match.groups()
            else:
                match2 = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*(.*)$", req_clean)
                if match2:
                    dep_name, dep_spec = match2.groups()
                else:
                    continue
            dep_name = normalize_package_name(dep_name)
            try:
                spec = SpecifierSet(dep_spec)
            except Exception:
                spec = SpecifierSet()
            dependencies.append((dep_name, spec))
        return dependencies
    except importlib.metadata.PackageNotFoundError:
        return []


def build_dependency_graph(target_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    """Scan the target directory for Python/Node manifests and construct a transitive dependency constraint graph."""
    graph: Dict[str, List[Dict[str, Any]]] = {}

    if not target_dir:
        return graph

    target_path = Path(target_dir)
    if not target_path.exists():
        return graph

    if target_path.is_file():
        target_path = target_path.parent

    # 1. Search for python requirements
    req_files = ["requirements.txt", "requirements-dev.txt"]
    for req_name in req_files:
        p = target_path / req_name
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        parsed = parse_requirement_line(line)
                        if parsed:
                            name, spec = parsed
                            graph.setdefault(name, []).append({
                                "parent": "root",
                                "specifier": spec
                            })

                            # Transitive resolution
                            for dep_name, dep_spec in get_python_transitive_dependencies(name):
                                graph.setdefault(dep_name, []).append({
                                    "parent": name,
                                    "specifier": dep_spec
                                })
            except Exception:
                pass

    # 2. Search for Node.js package-lock.json / package.json
    lock_path = target_path / "package-lock.json"
    pkg_path = target_path / "package.json"

    if lock_path.exists():
        try:
            relations = parse_package_lock(str(lock_path))
            for parent, children in relations.items():
                for child_name, semver_str in children:
                    spec = semver_to_pep440(semver_str)
                    graph.setdefault(child_name, []).append({
                        "parent": parent,
                        "specifier": spec
                    })
        except Exception:
            pass
    elif pkg_path.exists():
        try:
            relations = parse_package_json(str(pkg_path))
            for parent, children in relations.items():
                for child_name, semver_str in children:
                    spec = semver_to_pep440(semver_str)
                    graph.setdefault(child_name, []).append({
                        "parent": parent,
                        "specifier": spec
                    })
        except Exception:
            pass

    return graph


def validate_remediation(remediation_str: str, graph: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Validate a remediation string against a dependency graph, yielding safety status and alternative actions."""
    res = {
        "safe_to_apply": True,
        "compatible_range": None,
        "alternatives": []
    }

    parsed = parse_remediation_suggestion(remediation_str)
    if not parsed:
        return res

    pkg_name, target_version = parsed
    if pkg_name not in graph:
        return res

    constraints = graph[pkg_name]
    specifiers = [c["specifier"] for c in constraints]

    clean_target = clean_version_string(target_version)

    is_safe = True
    try:
        ver = Version(clean_target)
        for c in constraints:
            spec = c["specifier"]
            if ver not in spec:
                is_safe = False
                break
    except Exception:
        # Fall back to safe if parsing error happens to prevent blocking valid tools
        pass

    if not is_safe:
        res["safe_to_apply"] = False

        # Combine all constraints to show the allowed range
        combined_parts = []
        for c in constraints:
            for spec in c["specifier"]:
                combined_parts.append(str(spec))
        res["compatible_range"] = ", ".join(combined_parts) if combined_parts else "N/A"

        # Determine which packages impose conflicting requirements
        try:
            ver = Version(clean_target)
            conflicting_parents = sorted(list({
                c["parent"] for c in constraints if ver not in c["specifier"]
            }))
        except Exception:
            conflicting_parents = sorted(list({c["parent"] for c in constraints}))

        for parent in conflicting_parents:
            if parent == "root":
                res["alternatives"].append(
                    f"Update root project constraints for '{pkg_name}' to allow version {target_version}."
                )
            else:
                res["alternatives"].append(
                    f"Upgrade parent package '{parent}' to a version that supports '{pkg_name}' version {target_version}."
                )
        res["alternatives"].append(
            f"Downgrade or keep '{pkg_name}' within compatible range: {res['compatible_range']}."
        )

    return res
