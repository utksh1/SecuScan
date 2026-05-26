-- Migration: 001_add_performance_indexes
-- Adds missing indexes to findings, reports, and audit_log tables
-- and a composite index on tasks for dashboard query performance.
--
-- Query plans improved:
--   - Dashboard severity counts: full table scan → indexed GROUP BY on findings.severity
--   - Dashboard running tasks: full scan + filter → idx_tasks_status_created
--   - Findings list: unindexed ORDER BY → idx_findings_discovered_at
--   - Reports list: unindexed ORDER BY → idx_reports_generated_at
--   - Audit log lookups: unindexed → idx_audit_timestamp, idx_audit_event_type

-- Tasks
CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at DESC);

-- Findings
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_task_id ON findings(task_id);
CREATE INDEX IF NOT EXISTS idx_findings_discovered_at ON findings(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_findings_plugin_id ON findings(plugin_id);
CREATE INDEX IF NOT EXISTS idx_findings_target ON findings(target);
CREATE INDEX IF NOT EXISTS idx_findings_task_severity ON findings(task_id, severity);

-- Reports
CREATE INDEX IF NOT EXISTS idx_reports_task_id ON reports(task_id);
CREATE INDEX IF NOT EXISTS idx_reports_generated_at ON reports(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);

-- Audit log
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_task_id ON audit_log(task_id);