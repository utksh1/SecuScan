# Dependency Vulnerability Audit Operator Guide

This guide describes how the dependency vulnerability audit system functions, the format of policy exception definitions, and how to run auditing/verification checks locally.

---

## 1. Exception Configuration Format

Vulnerability exceptions are maintained in the root directory under [.audit-config.yaml](../.audit-config.yaml).

To document a new exception (to temporarily allow a dependency vulnerability that blocks deployment in CI), add an entry under the `exceptions` block using the following format:

Vulnerability exceptions are maintained in the root directory under [.audit-config.yaml](../.audit-config.yaml).

To document a new exception (to temporarily allow a dependency vulnerability that blocks deployment in CI), add an entry under the `exceptions` block using the following format:

```yaml
exceptions:
  CVE-2026-99999:
    package: vulnerable-library
    severity: high
    reason: |
      The vulnerability requires usage of a specific API endpoint that is disabled in our environment.
      We are tracking the patch and plan to upgrade by the target date.
    expires_at: 2026-09-30
    approved_by: security-team
    approval_date: 2026-06-01
    ticket: https://github.com/Rakshak05/SecuScan/issues/211
```

### Exception Schema Fields

| Field Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **Vulnerability Key** *(e.g. `CVE-2026-99999`)* | String | Yes | The primary vulnerability identifier (CVE ID, GHSA ID, or package name) used for exception matching. |
| `package` | String | Yes | Name of the package containing the vulnerability. |
| `severity` | String | No | The severity level (`critical`, `high`, `medium`, `low`) of the vulnerability. |
| `reason` | String | Yes | Clear business and technical justification for why this vulnerability does not pose an immediate threat or why the risk is accepted. |
| `expires_at` | String (ISO-8601) | Yes | The expiry date of the exception (`YYYY-MM-DD`). In CI, expired exceptions will automatically fail the build unless `enforce_expiry` is set to `false`. |
| `approved_by` | String | Yes | The individual or team that reviewed and approved the exception. |
| `approval_date` | String (ISO-8601) | No | Date when the exception was approved. |
| `ticket` | String | No | URL to a tracking ticket, issue, or pull request. |

---

## 2. Triage Decision Table

When a new vulnerability appears in a dependency audit, use this table to decide the appropriate action.

### Decision Matrix

| Severity | Exploitable in Our Context? | Affected Scope | Recommended Action | Exception Required? |
|----------|---------------------------|---------------|-------------------|-------------------|
| Critical | Yes (active attack surface) | Production | **Block deployment** — fix or upgrade immediately | No |
| Critical | Unlikely (disabled feature, internal-only) | Development | **Exception with expiry** — document mitigation and set review date | Yes |
| High | Yes | Production | **Block deployment** — file security ticket and track fix | No |
| High | Mitigated by config or network controls | Any | **Exception with reason** — document mitigation and review quarterly | Yes |
| Medium | Yes | Production | **Block deployment** — schedule fix within 30 days | No |
| Medium | Dev-only dependency | Development | **Acknowledge** — no blocking, track in backlog | No |
| Low | Any | Any | **Acknowledge** — no blocking, review at next update cycle | No |
| Info | Any | Any | **Acknowledge** — informational only, no action | No |

### Decision Rules

**Always block (no exception):**
- Critical/High severity + active production exploitability
- Vulnerability with known RCE (remote code execution) vector
- Dependency that handles authentication or sensitive data

**Exception candidates:**
- Mitigated by WAF, network segmentation, or feature flags
- Development-only dependency that is not shipped in production artifacts
- Dependency used by a tool that is only invoked in controlled CI environments
- Vulnerability with no known exploit Proof-of-Concept

**Always acknowledge (no exception, no block):**
- Low/Info severity with no active context
- Vulnerability in a transitive dependency with no control over the upgrade path (document the constraint)

### Exception Review Cadence

All exceptions must include an `expires_at` date. Suggested review intervals:

| Vulnerability Type | Suggested Expiry |
|---|---|
| Critical with mitigations | 30 days |
| High with mitigations | 60 days |
| Medium dev-only | 90 days |
| High with no exploit PoC | 90 days |
| Low/Info (acknowledged) | 180 days |

Expired exceptions automatically fail the CI build when `enforce_expiry: true` is set in `.audit-config.yaml`.

### Filing a Security Ticket

When blocking a deployment for a Critical or High vulnerability:

1. Create a GitHub issue with label `type:security`
2. Link the CVE/GHSA in the description
3. Assign to the relevant team owner
4. Set a target fix date based on severity (Critical: 7 days, High: 30 days)
5. Add the issue URL to the exception `ticket` field while the fix is pending

---

## 3. Local Reproduction Commands

You can run the audit tools locally to verify dependency status and validate configuration files.

### Backend (Python/pip dependencies)

1. **Install requirements and developer dependencies**:
   ```bash
   pip install -r backend/requirements.txt -r backend/requirements-dev.txt
   ```

2. **Run `pip-audit` to generate the raw report**:
   ```bash
   pip-audit -r backend/requirements.txt --desc --format json > backend/pip-audit-report.json
   ```
   *(Note: Add `--include-dev` if you wish to run audits against development dependencies).*

3. **Verify results against configuration**:
   ```bash
   python scripts/check_pip_audit.py \
     --report backend/pip-audit-report.json \
     --config .audit-config.yaml
   ```

### Frontend (npm dependencies)

1. **Install requirements**:
   ```bash
   cd frontend
   npm ci
   ```

2. **Run `npm audit` to generate the JSON report**:
   ```bash
   npm audit --json > npm-audit-report.json
   ```

3. **Verify results against configuration**:
   ```bash
   python ../scripts/check_npm_audit.py \
     --report npm-audit-report.json \
     --config ../.audit-config.yaml
   ```

### Generating Software Bill of Materials (SBOM)

To generate a CycloneDX 1.4 compatible SBOM containing all frontend and backend dependencies, run:
```bash
python scripts/generate_sbom.py --output sbom.json --include-dev
```
