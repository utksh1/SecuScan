# SecuScan — Project Summary

> **Version:** 0.3.0 · **Last Updated:** 2026-03-25

---

## Executive Summary

SecuScan is a **local-first pentesting platform** with a React 18 + Vite frontend, Python FastAPI backend, and 7-plugin scanning engine. The project has evolved beyond its Oct 2025 MVP into a fully modernized application featuring a Neo-Brutalist UI, real-time SSE streaming, report generation, and an executive dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND — React 18 + Vite + TypeScript                        │
│  12 pages · 7 components · Neo-Brutalist aesthetic              │
│  SSE streaming · Framer Motion · Material Symbols               │
├─────────────────────────────────────────────────────────────────┤
│  BACKEND — Python FastAPI + SQLite                              │
│  14 modules · 18+ API endpoints · SSE broadcast                 │
│  Redis cache · PDF/CSV reporting · Rate limiting                │
├─────────────────────────────────────────────────────────────────┤
│  PLUGINS — 7 JSON-metadata tools · 3 safety tiers               │
│  20 presets · 43 fields · CLI command templates                 │
├─────────────────────────────────────────────────────────────────┤
│  DATA — SQLite (tasks, assets, findings, reports, attack sfc)   │
│  Filesystem (raw outputs, generated reports)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend SPA

### Pages (12)

| Page | File | Purpose |
|------|------|---------|
| Dashboard | `Dashboard.tsx` | Executive stats, activity stream, system health |
| Scanner | `Scanner.tsx` | Plugin selection and scan launcher |
| Tool Config | `ToolConfig.tsx` | Dynamic form from plugin metadata |
| Task Details | `TaskDetails.tsx` | Full result viewer with raw output |
| History | `History.tsx` | Paginated task list with filters |
| Findings | `Findings.tsx` | Severity-grouped vulnerability view |
| Attack Surface | `AttackSurface.tsx` | Exposure summary |
| Reports | `Reports.tsx` | PDF/CSV export per task |
| Assets | `Assets.tsx` | Discovered asset inventory |
| Settings | `Settings.tsx` | Network, sandbox, safety config |
| Compare Tasks | `CompareTasks.tsx` | Diff view between scans |
| Login | `Login.tsx` | Authentication gate |

### Components (7)

| Component | Purpose |
|-----------|---------|
| `AppShell.tsx` | Main layout wrapper |
| `Sidebar.tsx` | Navigation with tool categories |
| `ExecutiveStatsBar.tsx` | Dashboard KPI cards |
| `Background.tsx` | Page background styling |
| `ThemeContext.tsx` | Dark/light mode state |
| `ToastContext.tsx` | Notification system |
| `__tests__/` | Component test suite |

### Design System
- **Aesthetic:** Neo-Brutalist — thick borders, hard shadows, high-contrast
- **Colors:** Charcoal, Silver, Rag-Red, Amber, Blue, Green
- **Typography:** Monospaced headers, massive italicized titles
- **Motion:** Framer Motion synchronized animations
- **Icons:** Material Symbols

---

## Backend API

### Modules (14)

| Module | Responsibility |
|--------|---------------|
| `main.py` | FastAPI app + lifespan |
| `config.py` | Settings + environment |
| `database.py` | SQLite async wrapper (8 tables) |
| `models.py` | Pydantic v2 request/response schemas |
| `plugins.py` | JSON metadata registry + loader |
| `validation.py` | Command injection + path traversal prevention |
| `ratelimit.py` | Per-plugin hourly + concurrent limits |
| `executor.py` | Background task execution + SSE broadcast |
| `routes.py` | 18+ API endpoints |
| `cache.py` | Redis-backed response caching |
| `reporting.py` | PDF + CSV report generation |
| `Dockerfile` | Container build definition |
| `__init__.py` | Package init |
| `requirements.txt` | Python dependencies |

### Endpoints (18+)

| Method | Route | What it does |
|--------|-------|-------------|
| GET | `/api/v1/plugins` | List all plugins |
| GET | `/api/v1/plugin/{id}/schema` | Plugin UI schema |
| GET | `/api/v1/presets` | All plugin presets |
| POST | `/api/v1/task/start` | Start scan |
| GET | `/api/v1/task/{id}/status` | Task status |
| GET | `/api/v1/task/{id}/stream` | SSE live output |
| GET | `/api/v1/task/{id}/result` | Full result |
| GET | `/api/v1/task/{id}/report/csv` | CSV download |
| GET | `/api/v1/task/{id}/report/pdf` | PDF download |
| POST | `/api/v1/task/{id}/cancel` | Cancel task |
| DELETE | `/api/v1/task/{id}` | Delete task |
| GET | `/api/v1/tasks` | List tasks (paginated) |
| GET | `/api/v1/dashboard/summary` | Dashboard data |
| GET | `/api/v1/assets` | Asset inventory |
| GET | `/api/v1/findings` | Vulnerability findings |
| GET | `/api/v1/attack-surface` | Attack surface |
| GET | `/api/v1/reports` | Generated reports |
| GET | `/api/v1/settings` | Current settings |

---

## Plugin System (7 plugins)

| # | Plugin | ID | Safety | Presets | Fields |
|---|--------|----|--------|---------|--------|
| 1 | 🔍 Nmap | `nmap` | Safe | 5 | 8 |
| 2 | 🌐 HTTP Inspector | `http_inspector` | Safe | 2 | 3 |
| 3 | 🔐 TLS Inspector | `tls_inspector` | Safe | 3 | 7 |
| 4 | 📂 Dir Discovery | `dir_discovery` | Intrusive | 3 | 9 |
| 5 | 🔎 Nikto | `nikto` | Intrusive | 3 | 7 |
| 6 | 🧬 Nuclei | `nuclei` | Intrusive | 2 | 4 |
| 7 | 💉 SQLMap | `sqlmap` | Exploit | 2 | 5 |

**Totals:** 20 presets · 43 fields · 7 dependencies

---

## Tests

- **16 tests** pass (10 unit + 6 integration)
- Execution time: 0.36s
- Coverage: models, plugins, validation, API routes

---

## Quick Start

```bash
# Backend
cd /Users/Apple/Secuscan
source venv/bin/activate
python3 -m backend.main
# → http://127.0.0.1:8080

# Frontend (separate terminal)
cd frontend
npm run dev
# → http://localhost:3000
```

---

## What's Done vs What's Left

| ✅ Done | 🔲 Remaining |
|---------|-------------|
| 7 plugins | Plugin signature verification |
| 12-page React SPA | i18n support |
| Neo-Brutalist UI | Full Docker sandboxing verification |
| SSE live streaming | Advanced result parsing |
| PDF/CSV reports | CI/CD pipeline |
| Executive dashboard | E2E tests (Playwright) |
| Redis cache layer | Workflow automation |
| 16 automated tests | Code cleanup (legacy dirs) |
| Dark mode | Keyboard shortcuts |
| Task comparison | PWA offline support |

---

**Status:** Production-ready for local use  
**Repository:** [SecuScan on GitHub](https://github.com/utksh1/SecuScan)
