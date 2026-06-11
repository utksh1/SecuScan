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
