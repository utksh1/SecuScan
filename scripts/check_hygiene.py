#!/usr/bin/env python3
import os
import pathlib
import subprocess
import sys

VENV_NAMES = {".venv", "venv", ".venv-codex", "env", "venv_tests"}

def is_virtualenv_segment(segment):
    s = segment.lower()
    return (
        s in VENV_NAMES
        or s.startswith("venv")
        or s.startswith(".venv")
        or s.endswith("-venv")
        or s.endswith("_venv")
    )

def get_git_root():
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return pathlib.Path(res.stdout.strip()).resolve()
    except Exception:
        return pathlib.Path(__file__).parent.parent.resolve()

def get_tracked_files(git_root):
    try:
        res = subprocess.run(
            ["git", "ls-files"],
            cwd=git_root,
            capture_output=True,
            text=True,
            check=True
        )
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception as e:
        print(f"Error running git ls-files: {e}", file=sys.stderr)
        return []

def is_in_virtualenv(relative_path, git_root):
    # 1. Check path segments
    path_obj = pathlib.Path(relative_path)
    parts = path_obj.parts
    dir_parts = parts[:-1] if len(parts) > 1 else ()
    for part in dir_parts:
        if is_virtualenv_segment(part):
            return True

    # 2. Check physical folders up to git root for pyvenv.cfg
    abs_path = (git_root / relative_path).resolve()
    current = abs_path.parent
    while True:
        if (current / "pyvenv.cfg").exists():
            return True
        if current == git_root or current == current.parent:
            break
        current = current.parent

    return False

def is_pycache_or_pyc(relative_path):
    path_obj = pathlib.Path(relative_path)
    if path_obj.suffix == ".pyc":
        return True
    if "__pycache__" in path_obj.parts:
        return True
    return False

def main():
    git_root = get_git_root()
    tracked_files = get_tracked_files(git_root)

    violation_files = []

    for f in tracked_files:
        # Normalize to forward slashes for unified parsing
        normalized_path = f.replace("\\", "/")
        if is_pycache_or_pyc(normalized_path):
            if not is_in_virtualenv(normalized_path, git_root):
                violation_files.append(f)

    if violation_files:
        print("ERROR: Tracked Python cache files (__pycache__ or *.pyc) found in repository:")
        for f in violation_files:
            print(f"  - {f}")
        print("\nFix:")
        print("  git rm --cached <file>")
        print("  Add the pattern to .gitignore to prevent recommitting.")
        sys.exit(1)

    print("Repository hygiene check passed: no tracked __pycache__ or pyc files found.")
    sys.exit(0)

if __name__ == "__main__":
    main()
