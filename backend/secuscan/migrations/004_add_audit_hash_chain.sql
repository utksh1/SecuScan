-- Migration: 004_add_audit_hash_chain
-- Adds tamper-evident hash chaining to the audit_log table.
--
-- Column additions (prev_hash, entry_hash) are handled idempotently by the
-- startup code in database._create_schema using PRAGMA table_info checks,
-- following the same pattern as owner_id in migration 003.  That approach
-- is necessary because SQLite has no "ADD COLUMN IF NOT EXISTS" syntax and
-- executescript() aborts on a duplicate-column error.
--
-- This file only contains statements that are safe to re-run on every
-- startup: a CREATE INDEX IF NOT EXISTS on entry_hash for fast chain-head
-- lookups, and an UPDATE to keep the sentinel default consistent for any
-- rows that were inserted between the column addition and the first hashed
-- write (there should be none in practice, but the guard is harmless).

CREATE INDEX IF NOT EXISTS idx_audit_entry_hash ON audit_log(entry_hash);
