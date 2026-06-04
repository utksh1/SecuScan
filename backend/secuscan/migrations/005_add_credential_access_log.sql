-- Migration: 005_add_credential_access_log
-- Adds a dedicated table for tracking vault credential access events.
--
-- Design notes:
--   - credential_name stores only the name, never the plaintext secret value.
--   - access_type is one of: read | write | delete | list
--   - task_id is nullable — list/write/delete calls may not be task-scoped.
--   - owner_id mirrors the authenticated caller at the time of access.
--   - accessed_at uses SQLite's datetime('now') default for consistency.
--
-- This table intentionally has no ON DELETE CASCADE from credential_vault
-- so access history is preserved after a credential is deleted (the name
-- is a plain text copy, not a FK, by design).

CREATE TABLE IF NOT EXISTS credential_access_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    credential_name TEXT NOT NULL,
    access_type  TEXT NOT NULL,
    task_id      TEXT,
    owner_id     TEXT NOT NULL DEFAULT 'default',
    accessed_at  TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cred_access_name        ON credential_access_log(credential_name);
CREATE INDEX IF NOT EXISTS idx_cred_access_task_id     ON credential_access_log(task_id);
CREATE INDEX IF NOT EXISTS idx_cred_access_accessed_at ON credential_access_log(accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_cred_access_owner       ON credential_access_log(owner_id);
