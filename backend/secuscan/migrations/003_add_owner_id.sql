-- Migration: 003_add_owner_id
-- Introduces per-user / per-workspace ownership for tasks, findings, and
-- reports to close the Broken Object Level Authorization (BOLA) gap where any
-- caller could read, delete, or export any task/report by guessing its ID
-- (issue #401).
--
-- The owner_id columns themselves are added idempotently in database.py
-- (_create_schema), using PRAGMA table_info checks so re-running startup is
-- safe — SQLite has no "ALTER TABLE ... ADD COLUMN IF NOT EXISTS". This file
-- only contains statements that are safe to re-run on every startup:
--
--   1. A defensive backfill of any NULL owner_id to the shared default owner.
--      (New columns are added as NOT NULL DEFAULT 'default', so existing rows
--      are already backfilled; this guards against rows created by an older
--      build that may have added the column as nullable.)
--   2. Indexes used to keep owner-scoped list queries fast.
--
-- Keep the 'default' literal in sync with auth.DEFAULT_OWNER_ID.

UPDATE tasks    SET owner_id = 'default' WHERE owner_id IS NULL;
UPDATE findings SET owner_id = 'default' WHERE owner_id IS NULL;
UPDATE reports  SET owner_id = 'default' WHERE owner_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_owner    ON tasks(owner_id);
CREATE INDEX IF NOT EXISTS idx_findings_owner ON findings(owner_id);
CREATE INDEX IF NOT EXISTS idx_reports_owner  ON reports(owner_id);
