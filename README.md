<p align="center">
  <img src="assets/logo.png" alt="SecuScan Logo" width="200">
</p>

<h1 align="center">SecuScan</h1>

<p align="center">
  <strong>Local-first security scanning for learning, experimentation, and ethical pentesting workflows.</strong>
</p>

<p align="center">
  <a href="https://github.com/utksh1/SecuScan/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.11%2B-blue" alt="Python 3.11+">
  </a>
  <a href="https://github.com/utksh1/SecuScan/tree/main/frontend">
    <img src="https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb" alt="React and Vite">
  </a>
  <a href="https://github.com/utksh1/SecuScan">
    <img src="https://img.shields.io/badge/Status-Active%20Development-orange" alt="Active Development">
  </a>
</p>

## Project Purpose

SecuScan is an open source, plugin-driven platform for running security scans from your own machine. It combines a FastAPI backend, a React frontend, and a growing plugin system for recon, web, cloud, container, and reporting workflows.

The project is designed to be:

- Local-first: scan data stays on infrastructure you control.
- Contributor-friendly: frontend, backend, plugins, and docs all have clear entry points.
- Safety-aware: the product is built around ethical and learning-oriented usage.

## Who It Is For

- Students and GSSoC contributors who want a real-world full-stack open source security project.
- Security learners who want a UI-backed toolkit instead of only raw CLI flows.
- Developers and researchers who want to extend scanners, parsers, reports, or workflow automation.

## Core Areas

- Scan orchestration and API flows in `backend/secuscan`
- React UI and dashboard experience in `frontend/src`
- Plugin metadata and parser integrations in `plugins`
- Reports, exports, and result normalization across backend and frontend

## Repository Map

- `backend/`: FastAPI app, execution logic, database/config, plugin loading, workflows
- `frontend/`: React + Vite app, routes, pages, shared components, and test config
- `plugins/`: scanner metadata, parser code, and plugin-specific helpers
- `testing/backend/`: Python unit and integration tests plus backend test scripts
- `frontend/testing/`: frontend unit and end-to-end test files
- `docs/`: supporting project documentation
- `scripts/`: helper scripts for signing, benchmarking, and maintenance

## Prerequisites

For a fresh local setup, make sure your machine has:

- `python3` 3.11 or newer
- Node.js 20 or newer
- npm 10 or newer
- Docker Desktop or Docker Engine if you want the Compose workflow

If your machine has multiple Python versions installed, `./setup.sh` now looks for a compatible `python3` automatically. You can also force one explicitly with `PYTHON=/path/to/python3.11 ./setup.sh`.

The scripted local setup path was re-checked from a fresh clone with a compatible Python 3.11+ interpreter.

## Quick Start

Choose one local development path.

### Option 1: Simple Local Dev

This is the fastest way to get the app running for UI or backend contributions from a fresh clone.

```bash
git clone https://github.com/utksh1/SecuScan.git
cd SecuScan
chmod +x setup.sh start.sh
./setup.sh
./start.sh
```

After startup:

- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`

### Option 2: Docker Compose Stack

Use this if you want the containerized app stack with Postgres and Redis.

```bash
git clone https://github.com/utksh1/SecuScan.git
cd SecuScan
docker compose up --build
```

After startup:

- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8081`

### Troubleshooting / Common Issues

For more detailed Windows-specific setup and troubleshooting instructions, see the [Windows Contributor Development Guide](docs/windows_contributor_guide.md).

#### Python version issues

This project requires Python 3.11 or newer.

Check your Python version:

```bash
python --version
```

or:

```bash
python3 --version
```

Install Python 3.11+ if your current version is older.

Python downloads: https://www.python.org/downloads/

#### Virtual environment activation issues

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

**Windows PowerShell**

```powershell
venv\Scripts\Activate.ps1
```

**Windows Git Bash**

```bash
source venv/Scripts/activate
```

**Linux/macOS**

```bash
source venv/bin/activate
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then reopen the terminal and activate the virtual environment again.

#### Node.js version issues

This project requires Node.js 20 or newer.

Check your Node.js version:

```bash
node -v
```

Install Node.js 20+ if your current version is older.

Node.js downloads: https://nodejs.org/

#### Dependency installation issues

If dependency installation fails, try reinstalling dependencies:

```bash
npm install
```

If installation still fails, try clearing the npm cache:

```bash
npm cache clean --force
```

Then reinstall dependencies again:

```bash
npm install
```

For complete contributor workflow and coding guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

#### Environment variable issues

If the app fails because environment variables are missing, copy the example environment file if available:

```bash
cp .env.example .env
```

Then update the required values before starting the project.

#### Still stuck?

Before opening a setup issue, check:

* Python 3.11+
* Node.js 20+
* virtual environment is activated
* required `.env` files exist

## Manual Development Commands

### Backend

> **Python version:** `python3` in these commands must resolve to 3.11 or newer. If your system default is older, substitute the full path (e.g. `python3.11`, `python3.12`) or use `PYTHON=/path/to/python3.11 ./setup.sh` instead. Run `python3 --version` to check.

```bash
cp .env.example .env
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
python3 -m uvicorn backend.secuscan.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## Running Tests

### Backend tests

```bash
./testing/test_python.sh
```

### Frontend tests

```bash
cd frontend
npm run test
```

### Frontend end-to-end tests

```bash
cd frontend
npm run e2e
```

## New Contributors Start Here

If this is your first contribution, start with one of these areas:

- Docs: improve setup steps, fix outdated instructions, or clarify contributor guidance.
- Frontend polish: small UI fixes, loading states, empty states, and test coverage.
- Backend cleanup: validation, API consistency, workflow edge cases, and unit tests.
- Plugins: metadata fixes, parser improvements, and result normalization.

Good first places to read before coding:

- [Contribution Guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)
- [Plugin Catalogue](PLUGINS.md)
- [Product Specification](docs/PRODUCT_SPEC.md)

## Contribution Guidelines

Before opening a pull request:

1. Fork the repo and branch from `main`.
2. Pick an issue or discuss the change before starting large work.
3. Keep pull requests scoped and include tests when behavior changes.
4. Update docs if you change setup, APIs, workflows, or contributor-facing behavior.

Detailed contributor expectations live in [CONTRIBUTING.md](CONTRIBUTING.md).

## Detailed Documentation

Long-form product and planning material lives outside the main README so onboarding stays readable:

- [SecuScan Product Specification](docs/PRODUCT_SPEC.md)
- [Plugin Catalogue](PLUGINS.md)
- [Secure Deployment Guide](docs/SECURE_DEPLOYMENT.md)
- [Windows Contributor Development Guide](docs/windows_contributor_guide.md)


## Tech Stack

- Backend: FastAPI, Pydantic, Uvicorn, SQLite/Postgres, Redis
- Frontend: React 18, TypeScript, Vite, Vitest, Playwright
- Plugins: metadata-driven scanner integrations and parser modules

## Contact

For questions, contributor coordination, onboarding help, or setup issues, use [GitHub Issues](https://github.com/utksh1/SecuScan/issues).

For responsible disclosure of security issues, follow the private reporting guidance in [SECURITY.md](SECURITY.md).

## Responsible Use

SecuScan is intended for authorized security testing, education, and research. Do not use it against systems you do not own or explicitly have permission to assess.

## License

This project is released under the [MIT License](LICENSE).

## Licensing Notes

- `LICENSE` is the canonical legal text for this repository.
- Contributions merged into this repository are distributed under the same MIT License unless explicitly stated otherwise.
- Third-party tools, libraries, and external scanners referenced by SecuScan may have their own licenses and usage terms. Check upstream projects before redistributing bundled integrations.


---

## Troubleshooting & Local Setup Failsafe

Use these checks when local installation or launch fails.

### 1. Stale Local Vite Module Cache

**Symptoms:** Frontend changes do not appear in the browser, or Vite reports internal parsing or bundling errors.

**Fix:** Force Vite to ignore its stale cache and run a fresh reload:

```bash
cd frontend
npm run dev -- --force
```

### 2. Node Dependency Resolution Loops (`npm i` hanging/failing)

**Symptoms:** `npm install` reports dependency tree conflicts, peer dependency errors, or hangs indefinitely.

**Fix:** Retry with the legacy peer dependency resolver:

```bash
npm install --legacy-peer-deps
```

### 3. Missing or Mismatched Environment Variables

**Symptoms:** The frontend loads, but API requests fail or scans cannot connect to the backend.

**Fix:** Create a local `.env` file from the example file:

```bash
cp .env.example .env
```

### 4. Port 5173 Already in Use

**Symptoms:** Vite reports that port `5173` is already in use and switches to another port.

**Fix:** Stop the process using that port.

Windows PowerShell:

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess -Force
```

Linux or macOS:

```bash
kill "$(lsof -t -i:5173)"
```
