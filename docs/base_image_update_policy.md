# Base Image Update Policy

> **Scope:** This document covers the Docker base images used by the SecuScan
> backend (`python:3.11-slim-bookworm`) and frontend (`nginx:1.27-alpine`).
> It defines when and how those images must be updated to keep the container
> supply chain safe.

---

## 1. Why this matters

Base images inherit all OS-level packages from the upstream distribution.
New CVEs are published daily, and a pinned base image that was clean at build
time can become vulnerable within weeks. Failing to update means:

- Trivy scans will start failing the CRITICAL policy gate in CI.
- SecuScan containers may be deployed with known exploitable vulnerabilities.

---

## 2. Scheduled review cadence

| Trigger | Who | Action |
|---|---|---|
| Weekly (Monday CI cron) | CI bot | Trivy scans run automatically. If new CRITICALs appear, the `docker-image-scan` workflow fails and surfaces alerts in GitHub Actions/Security tab. |
| New upstream minor/patch release | Maintainer | Update the `FROM` line within **5 business days** of release. |
| Zero-day or CRITICAL CVE advisory | Maintainer / any contributor | Update within **24 hours** of public disclosure. |
| Quarterly | Maintainer | Full review of all pinned versions (OS packages, base tag, and digest). |

---

## 3. How to update a base image

### 3.1 Pull the latest tag and verify

```bash
# Backend
docker pull python:3.11-slim-bookworm
docker inspect python:3.11-slim-bookworm --format '{{index .RepoDigests 0}}'

# Frontend
docker pull nginx:1.27-alpine
docker inspect nginx:1.27-alpine --format '{{index .RepoDigests 0}}'
```

### 3.2 Update the Dockerfile

Change the `FROM` line in:

- `backend/Dockerfile`
- `frontend/Dockerfile`
Example (pinning by digest for full reproducibility):

```dockerfile
FROM python:3.11-slim-bookworm@sha256:<new-digest> AS base
```

> **Note:** Tag-only pins (`python:3.11-slim-bookworm`) are acceptable for
> development velocity; digest pins are required for any release/production
> build. The CI workflow accepts tag pins and will still catch new CVEs via
> the weekly cron.

### 3.3 Run scans locally before pushing

```bash
# Build and scan backend
docker build -t secuscan-backend:local ./backend
trivy image --severity CRITICAL,HIGH --ignore-unfixed secuscan-backend:local

# Build and scan frontend
docker build -t secuscan-frontend:local ./frontend
trivy image --severity CRITICAL,HIGH --ignore-unfixed secuscan-frontend:local
```

Install Trivy locally: https://aquasecurity.github.io/trivy/latest/getting-started/installation/

### 3.4 Open a pull request

The PR title should follow: `chore(docker): update base images YYYY-MM-DD`

Include in the PR description:

- Old tag/digest → new tag/digest
- Link to upstream changelog or CVE advisory (if emergency update)
- Trivy output showing zero CRITICALs before and after
---

## 4. Accepting a known vulnerability (suppression)

If a CVE is:

- **Unfixed upstream** (no patched version available), and
- **Not exploitable** in the SecuScan threat model (e.g., vulnerability is in
  a library component that SecuScan never calls)
…it may be suppressed with a Trivy `.trivyignore` entry. The entry **must**:

1. Reference the CVE ID and a comment explaining why it is not exploitable.
2. Include an `expires` date no more than 90 days out.
3. Be approved by a maintainer in a PR review.
Example `.trivyignore`:

```
# CVE-2024-XXXXX: affects libssl's QUIC path; SecuScan does not use QUIC.
# Re-evaluate when python:3.11-slim-bookworm ships OpenSSL ≥3.x.
# Expires: 2026-08-01
CVE-2024-XXXXX
```

---

## 5. Non-root user requirement

Both Dockerfiles **must** run application processes as a non-root user.
The CI hardening check (`hardening-check` job) enforces this automatically
and will fail if `id -u` inside the container returns `0`.

- Backend: user `secuscan` (UID 1001)
- Frontend: user `nginx` (UID 101, built into `nginx:*-alpine`)
If a new base image changes the default UID, update the Dockerfile and
this document accordingly.

---

## 6. Contacts

| Role | Contact |
|---|---|
| Security issues | Open a private advisory via GitHub Security tab |
| General update PRs | Open a standard pull request and tag a maintainer |
