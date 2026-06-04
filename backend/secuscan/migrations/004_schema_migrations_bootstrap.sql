-- Migration: 004_schema_migrations_bootstrap
-- Creates the schema_migrations tracking table that records every applied
-- migration file along with its SHA-256 checksum and the timestamp at which
-- it was applied.  This table is also managed by Database._ensure_migration_table()
-- in database.py; the CREATE IF NOT EXISTS guard here makes the file idempotent
-- so it can be replayed safely against an already-upgraded database.
--
-- Once this migration has been applied the migration runner will transition from
-- the legacy "re-run everything on every startup" mode to the Alembic-style
-- "skip already-applied files" mode.

CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    checksum TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schema_migrations_filename
    ON schema_migrations(filename);

CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at
    ON schema_migrations(applied_at DESC);
