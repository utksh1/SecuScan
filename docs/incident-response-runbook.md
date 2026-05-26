# Incident Response Runbook — SecuScan

## 1. Leaked Vault Keys

### Detection

- Check logs for unauthorized access: `grep "vault" logs/secuscan.log`
- Verify key usage timestamps in audit trail

### Response Steps

1. **Immediately revoke** the compromised key
2. **Rotate** all vault keys: generate new keys, re-encrypt stored secrets
3. **Invalidate** all active sessions and tokens
4. **Audit** which reports used the compromised key
5. **Notify** affected users

### Verification

```bash
# Confirm new key is active
python -m secuscan verify-vault-keys

# Confirm old key is revoked
python -m secuscan list-vault-keys --status
```

## 2. Compromised Plugins

### Detection

- Monitor plugin execution logs for anomalous behavior
- Check plugin integrity hashes

### Response Steps

1. **Isolate** — disable the plugin immediately
2. **Preserve logs** before any cleanup
3. **Audit** all scans that used the compromised plugin
4. **Restore** from last known clean state

### Verification

```bash
# List active plugins
python -m secuscan plugins --list

# Disable compromised plugin
python -m secuscan plugins --disable <plugin-name>
```

## 3. Restoring Clean State

1. Stop all running scans
2. Rotate all credentials
3. Re-validate plugin integrity
4. Run full test suite: `pytest tests/`
5. Confirm system health before resuming
