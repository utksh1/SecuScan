# SecuScan — Implementation Status

> Last updated: 2026-04-21

This file reflects the verified state of the repository.

---

## Overall Status

SecuScan provides a local-first pentesting platform with a **React + Vite** frontend and **FastAPI + SQLite** backend, including plugin-driven scans, reporting, encrypted vault storage, and workflow scheduling.

---

## Newly Completed Areas (2026-04-21)

- ✅ **Plugin integrity controls**
  - Checksum verification support
  - HMAC signature verification support
  - Optional strict enforcement via settings
  - Checksum fields populated for all bundled plugins

- ✅ **Credential vault encryption at rest**
  - Encrypted secret storage endpoints (`/api/v1/vault/*`)

- ✅ **Workflow automation + scheduling**
  - Workflow CRUD and manual run endpoints
  - Background scheduler loop and manual scheduler tick endpoint

- ✅ **Infrastructure and quality automation**
  - GitHub Actions CI workflow for backend + frontend
  - Playwright E2E smoke test and config
  - Concurrent scan benchmark script

- ✅ **Tool catalog integration updates**
  - Previously marked pending tools are no longer hard-disabled in frontend catalog data.

- ✅ **Health endpoint hardening**
  - Runtime Docker availability check now uses binary detection.

---

## Operational Toggles

- `SECUSCAN_ENFORCE_PLUGIN_SIGNATURES=true`
- `SECUSCAN_PLUGIN_SIGNATURE_KEY=<key>`
- `SECUSCAN_VAULT_KEY=<key>`

---

## Remaining Caveat

- Some tools still depend on external binaries being installed on the runtime host; plugin availability reports missing binaries per tool at runtime.
