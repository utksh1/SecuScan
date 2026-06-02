import os
import sys

# Add root directory to sys.path so we can import from scripts
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

from scripts.select_tests import classify_file, select_tests


def test_classify_file_backend():
    assert classify_file("backend/secuscan/main.py") == "BACKEND"
    assert classify_file("testing/backend/unit/test_select_tests.py") == "BACKEND"
    assert classify_file("pyproject.toml") == "BACKEND"
    assert classify_file("scripts/refresh_plugin_checksum.py") == "BACKEND"


def test_classify_file_frontend():
    assert classify_file("frontend/src/App.tsx") == "FRONTEND"
    assert classify_file("frontend/package.json") == "FRONTEND"


def test_classify_file_plugins():
    assert classify_file("plugins/nmap/metadata.json") == "PLUGINS"
    assert classify_file("plugins/zap/parser.py") == "PLUGINS"


def test_classify_file_docs():
    assert classify_file("README.md") == "DOCS"
    assert classify_file("docs/architecture.md") == "DOCS"
    assert classify_file("backend/README.md") == "DOCS"


def test_classify_file_shared_or_config():
    assert classify_file(".github/workflows/ci.yml") == "SHARED_OR_CONFIG"
    assert classify_file(".gitignore") == "SHARED_OR_CONFIG"
    assert classify_file("setup.sh") == "SHARED_OR_CONFIG"
    assert classify_file("docker-compose.yml") == "SHARED_OR_CONFIG"
    assert classify_file("scripts/check-artifacts.sh") == "SHARED_OR_CONFIG"


def test_select_tests_empty():
    # Empty changed file list must fall back to running everything
    assert select_tests([]) == (True, True)


def test_select_tests_backend_only():
    assert select_tests(["backend/secuscan/main.py"]) == (True, False)
    assert select_tests(
        ["backend/secuscan/main.py", "testing/backend/unit/test_models.py"]
    ) == (True, False)


def test_select_tests_frontend_only():
    assert select_tests(["frontend/src/App.tsx"]) == (False, True)
    assert select_tests(["frontend/src/App.tsx", "frontend/package.json"]) == (
        False,
        True,
    )


def test_select_tests_plugins_only():
    # Plugins only should run backend tests
    assert select_tests(["plugins/nmap/metadata.json"]) == (True, False)


def test_select_tests_docs_only():
    # Docs only should run no code tests
    assert select_tests(["README.md"]) == (False, False)
    assert select_tests(["README.md", "docs/architecture.md"]) == (False, False)


def test_select_tests_mixed_backend_frontend():
    # Mixed backend and frontend changes should run everything
    assert select_tests(["backend/secuscan/main.py", "frontend/src/App.tsx"]) == (
        True,
        True,
    )


def test_select_tests_mixed_backend_plugins():
    # Backend + plugins should only run backend tests
    assert select_tests(["backend/secuscan/main.py", "plugins/nmap/metadata.json"]) == (
        True,
        False,
    )


def test_select_tests_mixed_frontend_docs():
    # Frontend + docs should only run frontend tests
    assert select_tests(["frontend/src/App.tsx", "README.md"]) == (False, True)


def test_select_tests_shared_config_fallback():
    # Any shared config file triggers full suite fallback
    assert select_tests([".github/workflows/ci.yml"]) == (True, True)
    assert select_tests(["setup.sh", "backend/secuscan/main.py"]) == (True, True)
    assert select_tests([".gitignore", "frontend/src/App.tsx"]) == (True, True)


# ── Event-based logic (PR vs push) ────────────────────────────────────────────

def test_select_tests_pull_request_always_full_suite():
    """
    PRs must always run full suite to ensure required branch protection checks
    do not get marked as 'skipped'.
    """
    # Docs-only PR: still run full suite for safety
    assert select_tests(["README.md"], event_name="pull_request") == (True, True)
    # Backend-only PR: full suite (always)
    assert select_tests(["backend/secuscan/main.py"], event_name="pull_request") == (
        True,
        True,
    )
    # Frontend-only PR: full suite (always)
    assert select_tests(["frontend/src/App.tsx"], event_name="pull_request") == (
        True,
        True,
    )


def test_select_tests_push_uses_selective_skipping():
    """
    Push events (to main) can use selective skipping to optimize CI time.
    """
    # Push with docs-only: skip tests
    assert select_tests(["README.md"], event_name="push") == (False, False)
    # Push with backend: run backend only
    assert select_tests(["backend/secuscan/main.py"], event_name="push") == (True, False)
    # Push with frontend: run frontend only
    assert select_tests(["frontend/src/App.tsx"], event_name="push") == (False, True)
