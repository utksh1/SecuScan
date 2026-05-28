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
