# SecuScan Architecture Guide

## Overview

SecuScan is a plugin-driven security scanning platform built using:

- FastAPI backend
- React + Vite frontend
- Plugin-based execution system

The project follows a modular architecture where the frontend communicates with backend APIs, which then coordinate scan workflows and plugin execution.

---

# High-Level Architecture

Frontend → Backend API → Workflow Engine → Plugins → Results → Reports

---

# Frontend Architecture

The frontend is built with:

- React 18
- TypeScript
- Vite

Frontend responsibilities include:

- Scan configuration
- User interaction
- Dashboard rendering
- API communication
- Result visualization

Main frontend code lives in:

```text
frontend/src
```

---

# Backend Architecture

The backend uses FastAPI and handles:

- API routing
- Validation
- Scan orchestration
- Plugin loading
- Result normalization
- Report generation

Main backend code lives in:

```text
backend/secuscan
```

---

# Plugin System

Plugins are responsible for integrating scanning tools and parsers.

Plugin responsibilities include:

- Tool metadata
- Parser execution
- Scan result formatting
- Tool-specific helpers

Plugins live inside:

```text
plugins/
```

---

# Request Lifecycle

1. User configures scan in frontend
2. Frontend sends API request
3. Backend validates payload
4. Workflow engine starts task
5. Plugin executes scanner
6. Results normalized
7. Reports generated
8. Frontend displays results

---

# Repository Structure

| Folder | Responsibility |
|---|---|
| backend/ | API and workflows |
| frontend/ | User interface |
| plugins/ | Scanner integrations |
| testing/ | Automated tests |
| docs/ | Project documentation |

---

# Future Improvements

Potential future improvements include:

- Better plugin sandboxing
- Expanded reporting formats
- Workflow automation
- Enhanced scan scheduling