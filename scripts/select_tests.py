#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess

def get_changed_files():
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")

    commands = [
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        ["git", "diff", "--name-only", "HEAD~1"],
        ["git", "diff", "--name-only"],
    ]

    had_error = False

    for cmd in commands:
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            files = [
                line.strip()
                for line in res.stdout.splitlines()
                if line.strip()
            ]
            if files:
                return files
        except subprocess.CalledProcessError:
            had_error = True
    if had_error:
        print("Warning: Unable to determine changed files.")
    return []


def get_event_name():
    """
    Get the GitHub event name (push or pull_request).
    Defaults to 'push' for local/unknown environments.
    """
    return os.environ.get("GITHUB_EVENT_NAME", "push")


def classify_file(filepath):
    """
    Classifies a file path into a logical CI category.

    Categories:
    - DOCS: Documentation files (.md) - safe to skip for selective testing
    - FRONTEND: Frontend code and tests
    - PLUGINS: Plugin definitions
    - BACKEND: Backend code, tests, and Python configs
    - SHARED_OR_CONFIG: Shared configuration and CI workflow files - always requires full suite
    """
    filepath = filepath.strip()
    if not filepath:
        return "DOCS"

    # Convert backslashes to forward slashes for cross-platform robustness
    filepath = filepath.replace("\\", "/")

    # Check for docs first (both .md files anywhere and anything in docs/ directory)
    # SAFE to skip: documentation cannot affect code behavior
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
        or (
            filepath.startswith("scripts/")
            and not filepath.endswith("check-artifacts.sh")
        )
    ):
        return "BACKEND"

    # Any other files (root scripts, github workflows, config files)
    # UNSAFE to skip: these files affect CI behavior and shared configuration
    return "SHARED_OR_CONFIG"


def select_tests(files, event_name="push"):
    """
    Decides which test suites to run based on changed files and event type.

    Args:
        files: List of changed file paths
        event_name: GitHub event type ('pull_request' or 'push')

    Returns:
        Tuple of (run_backend: bool, run_frontend: bool)

    Logic:
    ------
    For PULL REQUESTS (PR checks are required for merge):
        - Always run full suite to ensure required checks pass
        - This prevents required checks from being marked "skipped" in branch protection
        - PR must be thoroughly tested before merge

    For PUSH events (push checks are informational):
        - Use selective skipping to save CI time on main/develop
        - Skip tests for docs-only changes
        - Still run full suite for shared config changes
    """
    # Added a warning message when no changed files are detected before falling back to the full test suite.
    if not files:
        print(
            "Warning: No changed files detected. "
            "Running full test suite as a safety fallback."
        )
        return True, True

    # CRITICAL: For pull requests, always run full suite
    # This ensures branch protection required checks pass (not skipped)
    if event_name == "pull_request":
        return True, True

    # For push events, use selective skipping to optimize CI time
    categories = {classify_file(f) for f in files}

    # If any changed file is SHARED_OR_CONFIG, run full suite
    # These files affect CI behavior and must be thoroughly tested
    if "SHARED_OR_CONFIG" in categories:
        return True, True

    # If there are both BACKEND and FRONTEND changes, run full suite
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
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"run_backend={backend_str}\n")
            f.write(f"run_frontend={frontend_str}\n")
        print(
            f"Written to GITHUB_OUTPUT: run_backend={backend_str}, run_frontend={frontend_str}"
        )
    else:
        print(f"run_backend={backend_str}")
        print(f"run_frontend={frontend_str}")


def main():
    parser = argparse.ArgumentParser(
        description="Determine which tests to run based on changed files and event type."
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="List of changed files. If not specified, git diff will be used to detect changes.",
    )
    parser.add_argument(
        "--event-name",
        default=None,
        help="GitHub event name (pull_request or push). If not specified, reads from GITHUB_EVENT_NAME env var.",
    )
    args = parser.parse_args()

    if args.files is not None:
        files = args.files
    else:
        files = get_changed_files()
        print(f"Detected changed files: {files}")

    event_name = args.event_name or get_event_name()
    print(f"Event type: {event_name}")

    run_backend, run_frontend = select_tests(files, event_name=event_name)
    write_outputs(run_backend, run_frontend)


if __name__ == "__main__":
    main()
