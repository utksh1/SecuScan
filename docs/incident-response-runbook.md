# Incident Response Runbook — SecuScan

## 1. Leaked Vault Keys

### Detection

- Check logs for unauthorized access: `grep "vault" logs/secuscan.log`
- Review audit trail in `backend/secuscan/vault.py` for key usage

### Response Steps

1. **Immediately rotate** the compromised key — set a new `SECUSCAN_VAULT_KEY` in your `.env` file
2. **Re-encrypt** stored credentials — delete and re-add all vault entries using the new key
3. **Invalidate** all active sessions by restarting the backend service
4. **Audit** which reports and scans ran during the exposure window
5. **Notify** affected users if credentials were accessed

### Secret Rotation Dry-Run Checklist

Before rotating production vault keys, perform a dry-run exercise to validate the process and reduce the risk of service disruption.

#### Preparation

- Identify all services, scripts, and automation that depend on `SECUSCAN_VAULT_KEY`
- Confirm access to deployment environments and secret management systems
- Create a temporary non-production vault key for testing
- Ensure recent backups of encrypted vault data are available
- Notify relevant team members about the dry-run window

#### Dry-Run Procedure

1. Generate a temporary replacement vault key in a staging or test environment
2. Update the environment configuration to use the temporary key
3. Re-encrypt a representative set of stored credentials
4. Restart affected services and verify normal startup behavior
5. Execute common workflows that require vault access
6. Review logs for encryption, decryption, or authentication errors
7. Document any manual steps, delays, or unexpected issues encountered

#### Validation

- Vault secrets can be encrypted and decrypted successfully
- No application startup failures occur after key replacement
- Existing integrations continue to function correctly
- Audit logs accurately record vault access events
- Recovery steps are documented and tested

#### Rollback Readiness

- Retain the previous key until validation is complete
- Verify that the original configuration can be restored quickly
- Confirm that backup data can be recovered if required

### Verification

```bash
# Confirm vault config is loaded correctly
grep "SECUSCAN_VAULT_KEY" .env

# Confirm backend starts without vault errors
python -m uvicorn backend.secuscan.main:app --reload

# Run vault-related tests
pytest testing/backend/unit -k "vault" -v
```

## 2. Compromised Plugins

### Detection

- Review plugin execution logs for anomalous behavior
- Check files in `plugins/` for unexpected changes

### Response Steps

1. **Isolate** — remove or rename the compromised plugin file immediately
2. **Preserve logs** before any cleanup: `cp logs/secuscan.log logs/secuscan.log.bak`
3. **Audit** all scans that used the compromised plugin via scan history
4. **Restore** plugin from last known clean git commit

### Verification

```bash
# List plugin files
ls plugins/

# Disable compromised plugin by moving its directory out of the active plugin tree
mv plugins/<plugin-name> plugins/<plugin-name>.disabled

# Restore clean plugin from git
git checkout main -- plugins/<plugin-name>

# Run plugin tests
pytest testing/backend/unit -k "plugin" -v
```

## 3. Restoring Clean State

1. Stop all running scans
2. Rotate all credentials in `.env`
3. Re-validate plugin files: `git diff main -- plugins/`
4. Run full test suite: `pytest testing/backend/unit`
5. Confirm system health before resuming operations
