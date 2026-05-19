# Contributing to SecuScan

Thank you for contributing to SecuScan. This project is open to first-time contributors, experienced open source maintainers, and GSSoC participants who want to work on a practical full-stack security platform.

SecuScan is built for learning, defensive security workflows, and ethical testing. Please keep all contributions aligned with authorized, consent-based use.

## Before You Start

- Start with a small, reviewable task if this is your first contribution.
- Read [README.md](README.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md) before opening a pull request.
- Read the repository [LICENSE](LICENSE) so you understand how contributions are distributed.
- If you want to work on a larger feature, open or comment on an issue first so effort does not overlap.
- If you are contributing through GSSoC, mention that in the issue or pull request so maintainers can guide scope and review expectations.

## Good First Contribution Areas

- Documentation fixes, setup clarification, and onboarding polish
- Frontend UX improvements in `frontend/src`
- Backend validation, test coverage, and API consistency in `backend/secuscan`
- Plugin metadata cleanup and parser improvements in `plugins`
- CI, test reliability, and developer experience

When issue labels are available, look for tags such as `good first issue`, `documentation`, `frontend`, `backend`, `plugin`, `help wanted`, or `gssoc`.

## Local Setup

### Prerequisites

- Python `3.11+`
- Node.js `20+` recommended
- `npm`
- Docker optional for plugins that depend on containerized tooling

### Recommended Setup

```bash
./setup.sh
./start.sh
```

This starts:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/docs`

### Manual Setup

Backend:

> **Python version:** `python3` below must resolve to 3.11 or newer. Run `python3 --version` to check. If your system default is older, substitute the full path (e.g. `python3.11`) or use `PYTHON=/path/to/python3.11 ./setup.sh` instead of the manual steps.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
python3 -m uvicorn backend.secuscan.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## Project Layout

- `backend/secuscan`: FastAPI routes, execution logic, workflows, validation, vault, and reporting
- `frontend/src`: React pages, app shell, scan flows, settings, and tests
- `plugins`: plugin metadata, parser code, and tool-specific helpers
- `testing/backend`: backend unit and integration coverage
- `frontend/testing`: frontend unit and Playwright coverage
- `.github`: issue templates, PR template, and CI workflow

## Development Workflow

1. Fork the repository and create a branch from `main`.
2. Pick an issue or open one before starting large work.
3. Keep the change focused. Small PRs get reviewed much faster than broad rewrites.
4. Update tests and docs when behavior changes.
5. Open a pull request with a clear description, linked issue, and screenshots for UI changes.

Branch names can be simple and descriptive, such as:

- `docs/improve-contributing-guide`
- `fix/task-status-api`
- `feat/plugin-validation`

## Pull Request Format

Please follow the repository PR template and keep the submission easy to review.

Recommended PR title format:

- `docs: improve contributing guide`
- `fix(api): validate task status input`
- `feat(frontend): add scan empty state`

Your PR should include:

- A short description of the problem being solved
- A summary of the approach you took
- Linked issue references such as `Closes #123` or `Related to #123`
- A clear list of tests you ran
- Screenshots or short recordings for visible UI changes
- Notes about documentation, migrations, environment variables, or breaking behavior when relevant

Try to keep one pull request focused on one problem. If a change touches unrelated areas, split it into separate PRs when possible.

## Contribution Scoring

Every merged pull request can be scored for GSSoC using labels applied by the project admin or mentor. The scoring engine reads these labels after the PR is merged, so contributors should focus on clear scope, good implementation, and complete review notes rather than self-assigning score labels.

### Labels the Admin Applies

Each merged PR should have one difficulty label:

- `level:beginner`
- `level:intermediate`
- `level:advanced`
- `level:critical`

Optional quality labels can increase the contributor score:

- `quality:clean`
- `quality:exceptional`

Optional type bonus labels can describe the work category:

- `type:docs`
- `type:testing`
- `type:accessibility`
- `type:performance`
- `type:security`
- `type:design`
- `type:refactor`
- `type:devops`
- `type:bug`
- `type:feature`

Validation labels are decided by the admin:

- `gssoc:approved`
- `gssoc:invalid`
- `gssoc:spam`
- `gssoc:ai-slop`

Use `mentor:username` to credit the reviewing mentor with points for that PR.

### Contributor Points per PR

| Label | Points |
| --- | ---: |
| `level:beginner` | 20 pts |
| `level:intermediate` | 35 pts |
| `level:advanced` | 55 pts |
| `level:critical` | 80 pts |
| `quality:clean` | x 1.2 multiplier |
| `quality:exceptional` | x 1.5 multiplier |

Contributor score formula:

```text
((difficulty x quality) + type bonus)
```

### Mentor Points per Reviewed PR

| Label | Points |
| --- | ---: |
| `level:beginner` | 10 pts |
| `level:intermediate` | 20 pts |
| `level:advanced` | 30 pts |
| `level:critical` | 50 pts |
| `quality:clean` | +5 pts bonus |
| `quality:exceptional` | +10 pts bonus |

Mentor score formula:

```text
(base points + quality bonus)
```

## Commit Message Conventions

Use clear, imperative commit messages. Keep the first line short and descriptive.

Preferred format:

```text
type(scope): short summary
```

Examples:

- `feat(frontend): add task result empty state`
- `fix(backend): reject invalid workflow payloads`
- `docs(readme): clarify local setup steps`

Recommended commit types:

- `feat`
- `fix`
- `docs`
- `test`
- `refactor`
- `chore`

Guidelines:

- Use the imperative mood, such as `add`, `fix`, `update`, or `remove`
- Keep the subject line around 72 characters or fewer
- Reference the issue number in the commit body when useful
- Avoid vague messages like `changes`, `update code`, or `fix stuff`

## Licensing Expectations

By submitting a contribution, you agree that your changes can be distributed under the repository's MIT License.

Please avoid:

- Copying code from sources with incompatible licenses
- Adding assets, snippets, or templates without checking reuse permissions
- Introducing third-party dependencies without confirming their license is acceptable for this project

If you are unsure about a dependency or asset license, ask in the issue or pull request before merging it into the project.

## Test Expectations

Run the smallest relevant test set for your change, then broaden if needed.

Backend tests:

```bash
./testing/test_python.sh
```

Frontend unit tests:

```bash
cd frontend
npm run test
```

Frontend production build:

```bash
cd frontend
npm run build
```

Backend API smoke tests with the server running:

```bash
./testing/test_backend.sh
```

Optional frontend E2E:

```bash
cd frontend
npm run e2e
```

What we expect before review:

- Backend changes should run `./testing/test_python.sh`
- Frontend changes should run `npm run test` and `npm run build` in `frontend/`
- API or behavior changes should include either automated coverage or a short manual verification note
- Docs-only changes usually do not need full test runs, but please say that clearly in the PR
- If you could not run a recommended test, mention what you skipped and why

## Code Style

Please match the conventions already used in the repo instead of introducing a new style.

- Python:
  - Follow PEP 8 and prefer explicit, readable code
  - Use type hints where they improve clarity
  - Keep validation close to request and model boundaries
  - Prefer small functions over large, multi-purpose blocks
- Frontend:
  - Use TypeScript and functional React components
  - Keep component logic readable and avoid unnecessary abstraction
  - Reuse shared UI patterns when they already exist
  - Include accessible labels, states, and error handling for form changes
- Tests:
  - Add or update tests when behavior changes
  - Keep fixtures focused and easy to understand
- Docs:
  - Update contributor-facing docs when setup, workflow, or commands change
  - Prefer concrete examples over generic instructions

## Review Timeline

Reviews are handled on a best-effort basis.

Typical expectations:

- Initial maintainer response: within 3 business days for small, clearly scoped PRs
- Follow-up review after updates: usually within 2 to 4 business days
- Large PRs, release periods, or security-sensitive work may take longer

If a PR has been quiet for more than a week, a polite follow-up comment is completely fine.

## Review Etiquette

- Be kind, specific, and technical in review comments.
- Assume good intent and focus feedback on the code, docs, or behavior.
- If a maintainer asks for changes, update the PR instead of opening a new one unless requested.
- If you become inactive on a claimed issue, maintainers may reassign it so progress continues.

## Need Help?

- Use GitHub issues for bugs, enhancements, and scoped task discussion.
- Use pull request comments for implementation-specific review discussion.
- For security-sensitive reports, do not use public issues. Follow [SECURITY.md](SECURITY.md).

Thank you for helping make SecuScan more useful, safer, and more welcoming to new contributors.
## Frontend Generated Artifacts

Never commit these auto-generated paths:
- `frontend/dist/`
- `frontend/playwright-report/`
- `frontend/test-results/`
- `frontend/.vite/`
- `.vite/deps/`

If CI fails, run:
```bash
git rm --cached <file>
echo 'frontend/dist/' >> .gitignore