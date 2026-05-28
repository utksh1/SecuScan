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

### Verification

```bash
# Confirm vault config is loaded correctly
grep "SECUSCAN_VAULT_KEY" .env

# Confirm backend starts without vault errors
python -m uvicorn backend.secuscan.main:app --reload

# Run vault-related tests
pytest tests/ -k "vault" -v
```

## 2. Compromised Plugins

### Detection

- Review plugin execution logs for anomalous behavior
- Check plugin files in `backend/secuscan/plugins/` for unexpected changes

### Response Steps

1. **Isolate** — remove or rename the compromised plugin file immediately
2. **Preserve logs** before any cleanup: `cp logs/secuscan.log logs/secuscan.log.bak`
3. **Audit** all scans that used the compromised plugin via scan history
4. **Restore** plugin from last known clean git commit

### Verification

```bash
# List plugin files
ls backend/secuscan/plugins/

# Disable compromised plugin by removing it
rm backend/secuscan/plugins/<plugin-name>.py

# Restore clean plugin from git
git checkout main -- backend/secuscan/plugins/<plugin-name>.py

# Run plugin tests
pytest tests/ -k "plugin" -v
```

## 3. Restoring Clean State

1. Stop all running scans
2. Rotate all credentials in `.env`
3. Re-validate plugin files: `git diff main -- backend/secuscan/plugins/`
4. Run full test suite: `pytest tests/`
5. Confirm system health before resuming operations
