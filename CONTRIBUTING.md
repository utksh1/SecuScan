# Contributing to SecuScan

Thank you for contributing to SecuScan. This project is open to first-time contributors, experienced open source maintainers, and GSSoC participants who want to work on a practical full-stack security platform.

SecuScan is built for learning, defensive security workflows, and ethical testing. Please keep all contributions aligned with authorized, consent-based use.

---

# Before You Start

* Start with a small, reviewable task if this is your first contribution.
* Read `README.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` before opening a pull request.
* Read the repository `LICENSE` so you understand how contributions are distributed.
* If you want to work on a larger feature, open or comment on an issue first so effort does not overlap.
* If you are contributing through GSSoC, mention that in the issue or pull request so maintainers can guide scope and review expectations.

---

# Good First Contribution Areas

* Documentation fixes, setup clarification, and onboarding polish
* Frontend UX improvements in `frontend/src`
* Backend validation, test coverage, and API consistency in `backend/secuscan`
* Plugin metadata cleanup and parser improvements in `plugins`
* CI, test reliability, and developer experience

When issue labels are available, look for tags such as:

* `good first issue`
* `documentation`
* `frontend`
* `backend`
* `plugin`
* `help wanted`
* `gssoc`

---

# Local Setup

## Prerequisites

* Python `3.11+`
* Node.js `20+` recommended
* `npm`
* Docker (optional for plugins that depend on containerized tooling)

---

## Recommended Setup

```bash
./setup.sh
./start.sh
```

This starts:

* Backend: `http://127.0.0.1:8000`
* Frontend: `http://127.0.0.1:5173`
* API Docs: `http://127.0.0.1:8000/docs`

---

# Manual Setup

## Backend

Python version: `python3` below must resolve to `3.11+`.

Check version:

```bash
python3 --version
```

If your system default is older, substitute the full path (e.g. `python3.11`) or use:

```bash
PYTHON=/path/to/python3.11 ./setup.sh
```

### Setup Commands

```bash
python3 -m venv venv
source venv/bin/activate

pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt

python3 -m uvicorn backend.secuscan.main:app \
  --reload \
  --host 127.0.0.1 \
  --port 8000
```

---

## Frontend

```bash
cd frontend

npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

---

# Backend Testing Quickstart

This section explains how to run the backend test suite from a fresh checkout without touching the main development environment.

---

## 1. Prerequisites

Make sure your machine has Python `3.11+`.

```bash
python3 --version
```

If the version shown is older than `3.11`, substitute the full path to a compatible interpreter (e.g. `python3.11`) wherever `python3` appears below.

---

## 2. Run the Full Backend Test Suite

From the repo root:

```bash
./testing/test_python.sh
```

This script automatically:

* Creates an isolated virtual environment at `venv_tests/`
* Installs dependencies from:

  * `backend/requirements.txt`
  * `backend/requirements-dev.txt`
* Runs the full `testing/backend/` suite with `pytest`

You do not need to activate any virtual environment manually.

---

## 3. Run a Single Test File

```bash
source venv_tests/bin/activate

python -m pytest testing/backend/unit/test_models.py -v

deactivate
```

Replace `test_models.py` with whichever file you want to target.

* Unit tests: `testing/backend/unit/`
* Integration tests: `testing/backend/integration/`

> Run `./testing/test_python.sh` at least once before using this shortcut.

---

## 4. Requirements Files

| File                           | Purpose                           |
| ------------------------------ | --------------------------------- |
| `backend/requirements.txt`     | Core runtime dependencies         |
| `backend/requirements-dev.txt` | Test and development dependencies |

Both files must be installed for the test suite to run correctly.

---

## 5. Common Dependency Issues

### `ModuleNotFoundError`

The `venv_tests/` environment may be outdated.

Fix:

```bash
rm -rf venv_tests
./testing/test_python.sh
```

---

### `python3` Resolves to an Older Version

Check:

```bash
python3 --version
```

Use `python3.11` or `python3.12` explicitly if needed.

---

### Permission Denied on Test Script

```bash
chmod +x testing/test_python.sh
```

---

# Project Layout

| Path               | Purpose                                          |
| ------------------ | ------------------------------------------------ |
| `backend/secuscan` | FastAPI routes, workflows, validation, reporting |
| `frontend/src`     | React pages, scan flows, settings, tests         |
| `plugins`          | Plugin metadata and parser helpers               |
| `testing/backend`  | Backend unit and integration coverage            |
| `frontend/testing` | Frontend unit and Playwright coverage            |
| `.github`          | Templates and CI workflows                       |

---

# Development Workflow

1. Fork the repository and create a branch from `main`
2. Pick an issue or open one before starting large work
3. Keep changes focused and reviewable
4. Update tests and docs when behavior changes
5. Open a PR with:

   * Clear description
   * Linked issue
   * Screenshots for UI changes

### Example Branch Names

```text
docs/improve-contributing-guide
fix/task-status-api
feat/plugin-validation
```

---

# Pull Request Format

Recommended PR title format:

```text
docs: improve contributing guide
fix(api): validate task status input
feat(frontend): add scan empty state
```

Your PR should include:

* Problem being solved
* Summary of approach
* Linked issue references
* Tests you ran
* Screenshots/recordings for UI changes
* Notes about docs, migrations, env vars, or breaking behavior

Try to keep one PR focused on one problem.

---

# Contribution Scoring

Every merged PR can be scored for GSSoC using labels applied by maintainers.

---

## Difficulty Labels

* `level:beginner`
* `level:intermediate`
* `level:advanced`
* `level:critical`

---

## Quality Labels

* `quality:clean`
* `quality:exceptional`

---

## Type Bonus Labels

* `type:docs`
* `type:testing`
* `type:accessibility`
* `type:performance`
* `type:security`
* `type:design`
* `type:refactor`
* `type:devops`
* `type:bug`
* `type:feature`

---

## Validation Labels

* `gssoc:approved`
* `gssoc:invalid`
* `gssoc:spam`
* `gssoc:ai-slop`

---

## Contributor Score Formula

```text
((difficulty × quality) + type bonus)
```

---

## Mentor Score Formula

```text
(base points + quality bonus)
```

---

# Commit Message Conventions

Preferred format:

```text
type(scope): short summary
```

### Examples

```text
feat(frontend): add task result empty state
fix(backend): reject invalid workflow payloads
docs(readme): clarify local setup steps
```

### Recommended Commit Types

* `feat`
* `fix`
* `docs`
* `test`
* `refactor`
* `chore`

### Guidelines

* Use imperative mood (`add`, `fix`, `update`)
* Keep subject line under ~72 characters
* Avoid vague messages like:

  * `changes`
  * `update code`
  * `fix stuff`

---

# Licensing Expectations

By submitting a contribution, you agree that your changes can be distributed under the repository's MIT License.

Please avoid:

* Copying incompatible licensed code
* Adding unverified assets/snippets/templates
* Introducing dependencies without checking license compatibility

If unsure, ask in the issue or PR before merging.

---

# Test Expectations

Run the smallest relevant test set for your change.

---

## Backend Tests

```bash
./testing/test_python.sh
```

---

## Frontend Unit Tests

```bash
cd frontend
npm run test
```

---

## Frontend Production Build

```bash
cd frontend
npm run build
```

---

## Backend API Smoke Tests

```bash
./testing/test_backend.sh
```

---

## Optional Frontend E2E

```bash
cd frontend
npm run e2e
```

---

# Code Style

## Python

* Follow PEP 8
* Prefer explicit, readable code
* Use type hints where useful
* Prefer small focused functions

---

## Frontend

* Use TypeScript and functional React components
* Keep logic readable
* Reuse shared UI patterns
* Include accessible labels and error handling

---

## Tests

* Add/update tests when behavior changes
* Keep fixtures focused and understandable

---

## Docs

* Update contributor-facing docs when setup/workflow changes
* Prefer concrete examples over generic instructions

---

# Review Timeline

Typical expectations:

* Initial maintainer response: within 3 business days
* Follow-up review: within 2–4 business days

Large or security-sensitive PRs may take longer.

If a PR has been inactive for more than a week, a polite follow-up comment is acceptable.

---

# Review Etiquette

* Be kind, specific, and technical
* Focus feedback on code/docs/behavior
* Update the same PR when changes are requested
* Inactive claimed issues may be reassigned

---

# Need Help?

* Use GitHub Issues for:

  * Bugs
  * Enhancements
  * Task discussion

* Use PR comments for implementation-specific review discussion

For security-sensitive reports, follow `SECURITY.md`.

---

# PR Size & Generated Artifacts

We use an advisory GitHub Actions workflow to help maintain manageable PR sizes.

Never commit these generated paths:

```text
frontend/dist/
frontend/playwright-report/
frontend/test-results/
frontend/.vite/
.vite/deps/
```

If CI flags these folders, remove them using:

```bash
git rm -r --cached frontend/playwright-report/ frontend/test-results/ frontend/dist/

echo 'frontend/dist/' >> .gitignore
echo 'frontend/playwright-report/' >> .gitignore
echo 'frontend/test-results/' >> .gitignore
```

---

Thank you for helping make SecuScan more useful, safer, and more welcoming to contributors.
