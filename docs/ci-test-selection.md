## CI Test Selection (Changed-file scoped)

Purpose
-------
This document explains the changed-file scoped CI test selection implemented in `scripts/select_tests.py`.

## Branch Protection Safety Guarantee

**CRITICAL:** This implementation is safe for use with GitHub branch protection because:

1. **Pull Requests Always Run Full Suite**
   - All PR changes ALWAYS trigger the full test suite (backend + frontend)
   - This ensures required checks configured in branch protection never get marked as "skipped"
   - A skipped required check would incorrectly block the PR merge
   - Example: A docs-only PR still runs all tests to satisfy required checks

2. **Push Events Use Selective Skipping**
   - Only push events (commits to main/develop) use selective skipping
   - Push events are informational and don't block merges
   - Selective skipping saves CI time on post-merge verification
   - Example: A docs-only commit to main skips tests safely (no blocking rules)

## Event Type Behavior

| Event        | Docs-Only | Backend Only | Frontend Only | Mixed / Config  |
|--------------|-----------|--------------|---------------|-----------------|
| `pull_request` | ✓ Full Suite | ✓ Full Suite | ✓ Full Suite | ✓ Full Suite    |
| `push`       | ✗ Skip All | ✓ Backend    | ✓ Frontend    | ✓ Full Suite    |

Legend: ✓ = runs tests, ✗ = skips tests

## File Classification

The script classifies changed files into these categories:

- **DOCS** (skippable): `.md` files anywhere, `docs/` directory
  - Safe to skip because docs cannot affect code behavior
  - Exception: In PRs, still runs full suite for branch protection

- **FRONTEND**: `frontend/` directory
  - Runs frontend tests only (unless mixed with backend)

- **BACKEND**: `backend/`, `testing/backend/`, `pyproject.toml`, `scripts/*.py`
  - Runs backend tests; includes plugins via plugin dependencies

- **PLUGINS**: `plugins/` directory
  - Treated as backend changes (runs backend tests)

- **SHARED_OR_CONFIG** (forces full suite): `.github/`, root scripts, config files
  - `.github/workflows/` changes → full suite (CI behavior changes)
  - `setup.sh`, `docker-compose.yml` → full suite (system changes)
  - These affect multiple subsystems and must be fully tested

## Why This is Safe

1. **Conservative Fallbacks**
   - When in doubt, we run the full suite
   - Docs-only + shared config → full suite
   - Backend + frontend → full suite
   - Mixed categories → full suite

2. **Branch Protection Guaranteed**
   - PRs cannot skip required checks (always full suite)
   - Developers cannot accidentally merge untested code
   - Required checks will pass/fail, never be skipped

3. **Deterministic Classification**
   - File paths are mapped consistently
   - No heuristics or guessing
   - Can be verified locally

## Configuration

To modify the test selection policy:

1. Update file classification in `scripts/select_tests.py` → `classify_file()`
2. Update logic in `select_tests()` function
3. Add corresponding unit tests in `testing/backend/unit/test_select_tests.py`
4. Run tests locally: `pytest testing/backend/unit/test_select_tests.py -v`
5. Update this document if behavior changes

## Local Testing

Dry-run the selection tool locally:

```bash
# Test with specific files (simulating a PR/push)
python3 scripts/select_tests.py --files backend/main.py frontend/App.tsx --event-name pull_request
# Output: run_backend=true, run_frontend=true (PR always runs full suite)

python3 scripts/select_tests.py --files README.md --event-name push
# Output: run_backend=false, run_frontend=false (docs-only push skips tests)

python3 scripts/select_tests.py --files .github/workflows/ci.yml
# Output: run_backend=true, run_frontend=true (config changes run full suite)
```

## Required Checks in GitHub

For this to work correctly, configure your branch protection rule on `main` to require these checks:

- `formatting-hygiene` (always runs, PR-only)
- `backend-lint` (skippable based on changes)
- `backend-tests` (skippable based on changes)
- `frontend-checks` (skippable based on changes)

This allows:
- ✅ Docs-only PR → required checks (formatting) run, optional checks (tests) run full suite
- ✅ Backend-only PR → full suite runs, satisfying all required checks
- ✅ Docs-only push → tests skip safely (push checks are not required)
