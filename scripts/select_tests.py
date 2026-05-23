#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess

def get_changed_files():
    """
    Attempts to detect changed files using git diff.
    """
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")
    # Commands to try in order of preference
    commands = [
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        ["git", "diff", "--name-only", "HEAD~1"],
        ["git", "diff", "--name-only"],
    ]
    for cmd in commands:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            if files:
                return files
        except Exception:
            continue
    return []

def classify_file(filepath):
    """
    Classifies a file path into a logical CI category.
    """
    filepath = filepath.strip()
    if not filepath:
        return "DOCS"
    
    # Convert backslashes to forward slashes for cross-platform robustness
    filepath = filepath.replace("\\", "/")
    
    # Check for docs first (both .md files anywhere and anything in docs/ directory)
    if filepath.endswith(".md") or filepath.startswith("docs/"):
        return "DOCS"
    
    # Check for frontend files
    if filepath.startswith("frontend/"):
        return "FRONTEND"
    
    # Check for plugin files
    if filepath.startswith("plugins/"):
        return "PLUGINS"
    
    # Check for backend files
    if (
        filepath.startswith("backend/") 
        or filepath.startswith("testing/backend/") 
        or filepath == "pyproject.toml" 
        or (filepath.startswith("scripts/") and not filepath.endswith("check-artifacts.sh"))
    ):
        return "BACKEND"
    
    # Any other files (root scripts, github workflows, config files)
    return "SHARED_OR_CONFIG"

def select_tests(files):
    """
    Decides which test suites to run based on a list of changed files.
    Returns: (run_backend, run_frontend)
    """
    if not files:
        # Fall back to running the full suite to be safe
        return True, True
    
    categories = {classify_file(f) for f in files}
    
    # If any changed file is SHARED_OR_CONFIG, run the full suite
    if "SHARED_OR_CONFIG" in categories:
        return True, True
    
    # If there are both BACKEND and FRONTEND changes, run the full suite
    if "BACKEND" in categories and "FRONTEND" in categories:
        return True, True
    
    run_backend = False
    run_frontend = False
    
    # If BACKEND or PLUGINS changed, run backend tests
    if "BACKEND" in categories or "PLUGINS" in categories:
        run_backend = True
        
    # If FRONTEND changed, run frontend tests
    if "FRONTEND" in categories:
        run_frontend = True
        
    return run_backend, run_frontend

def write_outputs(run_backend, run_frontend):
    """
    Writes GITHUB_OUTPUT variables if the file exists, or prints to stdout.
    """
    output_file = os.environ.get("GITHUB_OUTPUT")
    backend_str = "true" if run_backend else "false"
    frontend_str = "true" if run_frontend else "false"
    
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"run_backend={backend_str}\n")
            f.write(f"run_frontend={frontend_str}\n")
        print(f"Written to GITHUB_OUTPUT: run_backend={backend_str}, run_frontend={frontend_str}")
    else:
        print(f"run_backend={backend_str}")
        print(f"run_frontend={frontend_str}")

def main():
    parser = argparse.ArgumentParser(description="Determine which tests to run based on changed files.")
    parser.add_argument(
        "--files",
        nargs="*",
        help="List of changed files. If not specified, git diff will be used to detect changes.",
    )
    args = parser.parse_args()
    
    if args.files is not None:
        files = args.files
    else:
        files = get_changed_files()
        print(f"Detected changed files: {files}")
        
    run_backend, run_frontend = select_tests(files)
    write_outputs(run_backend, run_frontend)

if __name__ == "__main__":
    main()
