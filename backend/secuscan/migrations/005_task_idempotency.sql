-- Migration 005: Add task_idempotency table for duplicate scan submission protection
-- Idempotency keys allow clients to safely retry POST /task/start without
-- creating duplicate scan tasks. A key is tied to an owner and expires after
-- a configurable TTL (default 24 hours).

CREATE TABLE IF NOT EXISTS task_idempotency (
    idempotency_key TEXT NOT NULL,
    task_id         TEXT NOT NULL,
    owner_id        TEXT NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    expires_at      TIMESTAMP NOT NULL,
    PRIMARY KEY (idempotency_key, owner_id)
);

-- Index to speed up the periodic purge of expired keys.
CREATE INDEX IF NOT EXISTS idx_idempotency_expires
    ON task_idempotency(expires_at);

-- Index to support per-owner lookups without a full table scan.
CREATE INDEX IF NOT EXISTS idx_idempotency_owner
    ON task_idempotency(owner_id);
