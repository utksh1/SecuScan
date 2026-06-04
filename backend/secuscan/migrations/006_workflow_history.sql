-- Migration: 006_workflow_history
-- Adds two tables for workflow governance:
--
-- workflow_versions  — a full snapshot of the workflow definition every time
--   PATCH /workflows/:id modifies it, preserving the history needed for rollback.
--   version_number is a per-workflow monotonic counter so rollback targets can be
--   identified by a stable integer.  definition_json stores the complete snapshot
--   (name, schedule_seconds, enabled, steps) so a rollback is a self-contained
--   restore and does not depend on diff-chaining.
--
-- workflow_runs  — one row per run_workflow_once() invocation, recording which
--   version was active at run time, the task IDs that were queued, and the
--   final status (pending → running → completed | failed | cancelled).

CREATE TABLE IF NOT EXISTS workflow_versions (
    id              TEXT PRIMARY KEY,
    workflow_id     TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    definition_json TEXT NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    created_by      TEXT NOT NULL DEFAULT 'system',
    UNIQUE(workflow_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_wf_versions_workflow ON workflow_versions(workflow_id, version_number DESC);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id              TEXT PRIMARY KEY,
    workflow_id     TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    version_id      TEXT REFERENCES workflow_versions(id) ON DELETE SET NULL,
    version_number  INTEGER,
    triggered_by    TEXT NOT NULL DEFAULT 'manual',
    status          TEXT NOT NULL DEFAULT 'pending',
    task_ids_json   TEXT NOT NULL DEFAULT '[]',
    started_at      TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    completed_at    TIMESTAMP,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_wf_runs_workflow   ON workflow_runs(workflow_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_wf_runs_status     ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_wf_runs_version_id ON workflow_runs(version_id);
