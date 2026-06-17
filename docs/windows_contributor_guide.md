# Windows Contributor Development Guide

## Overview

This guide helps Windows contributors set up SecuScan locally using PowerShell and common Windows development tools.

---

## Prerequisites

Install the following before starting:

* Python 3.11+
* Node.js 20+
* npm 10+
* Git
* Docker Desktop (optional)

Verify installations:

```powershell
python --version
node -v
npm -v
git --version
```

---

## WSL Guidance

Windows contributors can use PowerShell, Windows Terminal, or Git Bash for most
contribution workflows. Windows Subsystem for Linux (WSL) is not required for
general development.

### WSL Is Optional

WSL is optional for:

* Documentation updates
* Frontend development
* Backend development using the Windows Python installation
* Running Git commands
* Opening pull requests

### WSL Is Recommended

WSL may provide a smoother experience when:

* Running Linux-focused shell workflows
* Using Bash scripts extensively
* Working with Docker Desktop and WSL2 integration
* Reproducing issues that occur only in Linux environments

### WSL Is Out Of Scope

This guide focuses on native Windows development tools. WSL-specific setup,
Linux package management, and Linux distribution configuration are not covered
here.

---

## Clone the Repository

```powershell
git clone https://github.com/utksh1/SecuScan.git
cd SecuScan
```

If you are contributing from a fork, add the main repository as `upstream` so
you can rebase on the latest `main` before opening a pull request:

```powershell
git remote add upstream https://github.com/utksh1/SecuScan.git
git fetch upstream
```

---

## Backend Setup

### Create Virtual Environment

```powershell
python -m venv venv
```

### Activate Virtual Environment

#### PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

#### Git Bash

```bash
source venv/Scripts/activate
```

---

## Install Backend Dependencies

```powershell
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

---

## Run Backend

```powershell
python -m uvicorn backend.secuscan.main:app --reload --host 127.0.0.1 --port 8000
```

Backend should now run at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

If you prefer the repository helper scripts, run them from Git Bash instead of
PowerShell because they are shell scripts:

```bash
./setup.sh
./start.sh
```

---

## Frontend Setup

Move into the frontend directory:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Run the frontend:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

Frontend should now run at:

```text
http://127.0.0.1:5173
```

---

## Backend Test Workflow

Use the repository test script to create the isolated `venv_tests` environment
and install test dependencies:

```bash
./testing/test_python.sh
```

After the first run, you can execute a single backend test file directly.

#### PowerShell

```powershell
.\venv_tests\Scripts\Activate.ps1
python -m pytest testing/backend/test_task_pagination.py -v
deactivate
```

#### Git Bash

```bash
source venv_tests/Scripts/activate
python -m pytest testing/backend/test_task_pagination.py -v
deactivate
```

---

## Docker Setup (Optional)

Install Docker Desktop for Windows:

https://www.docker.com/products/docker-desktop/

During installation:

* Enable WSL2 integration if prompted
* Restart your system after installation

Verify Docker installation:

```powershell
docker --version
docker compose version
```

Run the project stack:

```powershell
docker compose up --build
```

If `docker compose` fails even though Docker Desktop is installed, open Docker
Desktop first and wait until the engine reports it is running.

---

## Common Windows Troubleshooting

### PowerShell Execution Policy Error

If virtual environment activation fails with:

```text
running scripts is disabled on this system
```

Run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then retry activation.

---

### Python PATH Issues

If `python` is not recognized:

* Reinstall Python
* Ensure "Add Python to PATH" is checked during installation

Verify again:

```powershell
python --version
```

---

### Node.js / npm Issues

Verify versions:

```powershell
node -v
npm -v
```

If commands fail:

* Reinstall Node.js
* Restart the terminal

---

### npm Dependency Installation Issues

Clear npm cache:

```powershell
npm cache clean --force
```

Reinstall dependencies:

```powershell
npm install
```

If Vite still fails to start after dependency updates, remove the existing
install and reinstall from scratch:

```powershell
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
```

---

### Git Bash vs PowerShell Command Mismatch

Use Git Bash for commands that rely on Unix shell syntax:

```bash
source venv/Scripts/activate
./testing/test_python.sh
```

Use PowerShell for Windows-native commands:

```powershell
.\venv\Scripts\Activate.ps1
```

---

### Port Already In Use

If the backend or frontend fails to start because the port is already in use,
find the conflicting process and stop it.

Check which process is using the port:

```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :5173
```

Stop the process by PID:

```powershell
taskkill /PID <PID> /F
```

---

## Git Workflow Basics

### Create a New Branch

```powershell
git checkout -b feature/my-feature-name
```

### Check Repository Status

```powershell
git status
```

### Stage Files

```powershell
git add .
```

### Commit Changes

```powershell
git commit -m "docs: update Windows contributor guide"
```

### Push Changes

```powershell
git push origin feature/my-feature-name
```

---

## Git Rebase Conflict Basics

Update your branch with the latest upstream changes:

```powershell
git pull --rebase upstream main
```

If `upstream` does not exist yet, confirm your remotes first:

```powershell
git remote -v
```

If conflicts appear:

1. Open conflicted files
2. Resolve conflicts manually
3. Stage resolved files:

```powershell
git add .
```

4. Continue rebase:

```powershell
git rebase --continue
```

Abort rebase if necessary:

```powershell
git rebase --abort
```

---

## Recommended Development Tools

### Recommended Terminals

* PowerShell
* Windows Terminal

Optional:

* Git Bash

### Recommended VS Code Extensions

* Python
* Pylance
* ESLint
* Prettier
* Docker
* GitLens

---

## Additional Resources

* [README.md](../README.md)
* [CONTRIBUTING.md](../CONTRIBUTING.md)
* [SECURITY.md](../SECURITY.md)
* Docker Documentation: https://docs.docker.com/
* Python Documentation: https://docs.python.org/3/
* Node.js Documentation: https://nodejs.org/en/docs/

---

## Final Notes

Before opening a pull request:

* Ensure backend starts successfully
* Ensure frontend starts successfully
* Run tests if applicable
* Verify formatting and lint checks pass
* Keep pull requests focused and well-scoped

This guide is intended to help Windows contributors onboard faster and reduce common local setup issues.
