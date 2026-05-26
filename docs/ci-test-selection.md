## CI Test Selection (Changed-file scoped)

Purpose
-------
This document explains the changed-file scoped CI test selection implemented in `scripts/select_tests.py`.

Behavior
--------
- The script maps changed files to test subsets (backend, frontend, plugin tests, etc.).
- When a change touches only files mapped to a subset, CI runs that subset to save time.
- A full-suite fallback is used in these cases:
  - Repository-level shared config changes (eg: changes to `pyproject.toml`, `.github/`, or shared CI config files).
  - Documentation-only or push types explicitly configured to force full CI.
  - When the mapping cannot classify changed files deterministically.

Why this is safe
---------------
- The fallback exists to guarantee full verification when a change may affect CI orchestration or multiple subsystems.
- The mapping is conservative: it prefers running more tests rather than skipping them.

How to run locally
-------------------
Run the selection tool and dry-run tests locally:

```bash
./venv_tests/bin/python scripts/select_tests.py --dry-run --changed-files <list-of-files>
```

If you need this policy changed or to add new mappings, update `scripts/select_tests.py` and the unit tests under `testing/backend/unit/test_select_tests.py`.
