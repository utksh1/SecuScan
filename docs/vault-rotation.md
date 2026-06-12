# Vault Rotation

This document describes how to rotate the credential vault encryption key safely.

## Overview

SecuScan stores encrypted secrets in the `credential_vault` table. Each entry has
a `key_version` column indicating which key version encrypted the value. The
server supports a transactional rotation workflow that ensures either all
entries are re-encrypted with the new key, or none are modified.

## Important security notes

- Do not supply secret keys in API request bodies. The rotation endpoint
  intentionally requires the previous key to be present in the process
  environment (via `SECUSCAN_VAULT_KEY_PREVIOUS`) to avoid accidental leakage.
- Configure the previous key in the environment before triggering rotation.
- Rotation is atomic: if any record cannot be decrypted, the operation
  aborts and the database is rolled back.

## Operator workflow

1. Ensure the new vault seed is set via `SECUSCAN_VAULT_KEY` in the service
   environment.
2. Temporarily set the previous seed in `SECUSCAN_VAULT_KEY_PREVIOUS` (the
   same value previously used to encrypt existing secrets).
3. Call the rotation endpoint (once):

   POST /api/v1/vault/rotate

4. If the rotation succeeds, remove `SECUSCAN_VAULT_KEY_PREVIOUS` from the
   environment and keep the new key in `SECUSCAN_VAULT_KEY`.
5. Verify secrets are readable with `GET /api/v1/vault/{name}`.

## Failure modes

- If any vault record cannot be decrypted with the known keys, rotation will
  abort and report which record failed. No records will be partially
  re-encrypted.
- If the previous key is not provided via `SECUSCAN_VAULT_KEY_PREVIOUS`, the
  rotation endpoint will refuse to run.

## Testing locally

- To simulate rotation locally, set two env vars in your shell and start the
  server:

  export SECUSCAN_VAULT_KEY_PREVIOUS="old-seed"
  export SECUSCAN_VAULT_KEY="new-seed"

- Create a secret via the API, and then call the rotate endpoint.

## Notes

This implementation uses AES-GCM (via the `cryptography` package) and stores a
one-byte version prefix in the encrypted blob. The DB schema contains a
`key_version` integer column to track versions.
