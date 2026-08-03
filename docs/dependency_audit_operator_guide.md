# Dependency Vulnerability Audit Operator Guide

This guide describes how the dependency vulnerability audit system functions, the format of policy exception definitions, and how to run auditing/verification checks locally.

---

## 1. Exception Configuration Format

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

## 2. Local Reproduction Commands

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

---

## 3. Vulnerability Triage Decision Table

When an audit surfaces a finding, use the following table to classify it into one of three categories and determine the appropriate operator response. Classification is driven by severity, exploitability, and whether the affected package ships to production.

| Category | Criteria | Operator Action | Example |
| :--- | :--- | :--- | :--- |
| **Informational** | `low` severity findings with no exploit path, or findings confined to dev-only dependencies. | Note and monitor; no immediate action required. | A `low` CVE in a build-time dev dependency that is not shipped to production. |
| **Urgent** | `high` or `critical` findings with a known fix available, or a plausible exploit path in production dependencies. | Schedule a patch within the current sprint and file a tracking ticket. | A `high` CVE in a runtime HTTP library with a patched version released. |
| **Blocking** | `critical` findings with active exploitation, no available fix, or affecting authentication/secrets handling. | Stop deployment; apply mitigation or a temporary exception with security-team approval immediately. | A `critical` RCE in a core runtime dependency with no patch. |

Blocking findings that require a temporary allowance to unblock deployment must be documented using the exception format described in [Section 1](#1-exception-configuration-format).
