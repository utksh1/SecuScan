## CI Test Selection (Changed-file scoped)

Purpose
-------
This document explains the changed-file scoped CI test selection implemented in
`scripts/select_tests.py` and wired into the `detect-changes` job in
`.github/workflows/ci.yml`. For runnable, verified examples of targeted selection and
full-suite fallback, jump to
[Local testing and worked examples](#local-testing-and-worked-examples).

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

- **BACKEND**: `backend/`, `testing/backend/`, `pyproject.toml`, and **any file under
  `scripts/`** (regardless of extension) — except `scripts/check-artifacts.sh`
  - Runs backend tests; includes plugins via plugin dependencies

- **PLUGINS**: `plugins/` directory
  - Treated as backend changes (runs backend tests)

- **SHARED_OR_CONFIG** (forces full suite): `.github/`, root scripts/config files, and
  **anything that matches no category above**
  - `.github/workflows/` changes → full suite (CI behavior changes)
  - `setup.sh`, `docker-compose.yml`, root `Makefile` → full suite (system changes)
  - `scripts/check-artifacts.sh` → full suite (the one `scripts/` file kept out of BACKEND)
  - These affect multiple subsystems and must be fully tested

## Fallback Behavior

Changed-file detection lives **inside `scripts/select_tests.py`** — the `detect-changes`
job runs `python3 scripts/select_tests.py` directly (see `.github/workflows/ci.yml`),
so there is no separate `detect_changes.py`. When the workflow does not pass `--files`,
the script's `get_changed_files()` helper tries these git commands in order and uses the
first one that returns a non-empty list:

1. `git diff --name-only origin/<base>...HEAD` — PRs; `<base>` = `GITHUB_BASE_REF` (default `main`)
2. `git diff --name-only <base>...HEAD`
3. `git diff --name-only HEAD~1`
4. `git diff --name-only` — uncommitted working-tree changes

If every command fails (or all return nothing), `get_changed_files()` returns an
**empty list**, which `select_tests()` treats as "run everything." A detection failure
can therefore never silently skip tests.

> In CI the `detect-changes` job checks out with `fetch-depth: 0` and, for pull
> requests, fetches the base branch first, so commands (1)–(2) normally succeed.

### Detection fails or returns no files → full suite

An empty changed-files list is treated as "unknown," not "nothing changed," so both
`push` and `pull_request` fall back to the full suite. See the *Empty changeset* and
*pull request* examples under
[Local testing and worked examples](#local-testing-and-worked-examples).

### Git history unavailable (shallow clone)

Commands (1)–(3) need at least one ancestor commit. In a `git clone --depth=1` checkout
with a single commit they all fail, and command (4) sees no uncommitted changes, so
`get_changed_files()` returns `[]` → full suite. This is exactly why CI uses
`fetch-depth: 0` instead of a shallow clone.

### Unknown / unrecognized files → full suite

A path that matches no known prefix (not `docs/`, `frontend/`, `plugins/`, `backend/`,
…) is classified as **SHARED_OR_CONFIG**, which forces the full suite (see the *Unknown
file* example below). This is conservative: new or unclassified file types never bypass
CI.

## Why This is Safe

1. **Conservative Fallbacks**
   - When in doubt, we run the full suite
   - Docs-only + shared config → full suite
   - Backend + frontend → full suite
   - Mixed categories → full suite
   - Detection failure → full suite
   - Empty detection → full suite
   - Unknown file type → full suite

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

## Local testing and worked examples

Reproduce any selection decision locally with `--files` (to simulate a changeset) and
`--event-name` (to simulate the trigger). The comments below are the script's actual
stdout (`select_tests.py` prints `run_backend=...` / `run_frontend=...`).

### Targeted selection (push events)

On `push`, only the suites touched by the change run:

```bash
# Backend-only change → backend suite only
python3 scripts/select_tests.py --files backend/secuscan/routes.py --event-name push
# run_backend=true, run_frontend=false

# Frontend-only change → frontend checks only
python3 scripts/select_tests.py --files frontend/src/App.tsx --event-name push
# run_backend=false, run_frontend=true

# Plugin-only change → backend suite (plugins run under backend)
python3 scripts/select_tests.py --files plugins/nmap/metadata.json --event-name push
# run_backend=true, run_frontend=false

# Docs-only change → nothing runs (selective skip is push-only)
python3 scripts/select_tests.py --files docs/ci-test-selection.md --event-name push
# run_backend=false, run_frontend=false
```

### Full-suite fallback

The full suite runs whenever the change is mixed, touches shared config, cannot be
classified, produces no detected files, or the event is a pull request:

```bash
# Mixed backend + frontend → full suite
python3 scripts/select_tests.py --files backend/secuscan/routes.py frontend/src/App.tsx --event-name push
# run_backend=true, run_frontend=true

# Shared CI/config change → full suite
python3 scripts/select_tests.py --files .github/workflows/ci.yml --event-name push
# run_backend=true, run_frontend=true

# Unknown / unclassified file → full suite (treated as SHARED_OR_CONFIG)
python3 scripts/select_tests.py --files Makefile --event-name push
# run_backend=true, run_frontend=true

# Empty changeset (detection returned nothing) → full suite
python3 scripts/select_tests.py --files --event-name push
# run_backend=true, run_frontend=true

# Any pull request → full suite regardless of files (branch-protection safety)
python3 scripts/select_tests.py --files docs/ci-test-selection.md --event-name pull_request
# run_backend=true, run_frontend=true
```

> These exact decisions are asserted in
> [`testing/backend/unit/test_select_tests.py`](../testing/backend/unit/test_select_tests.py).
> Run them with `pytest testing/backend/unit/test_select_tests.py -v`.

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
