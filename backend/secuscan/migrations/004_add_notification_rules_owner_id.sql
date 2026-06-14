-- Migration: 004_add_notification_rules_owner_id
-- Adds owner_id column to notification_rules for per-workspace isolation
-- (issue #740). The column is added idempotently in database.py before this
-- migration runs (_ensure_column uses PRAGMA table_info + ALTER TABLE).
-- This migration handles the backfill and index for existing deployments.

UPDATE notification_rules SET owner_id = 'default' WHERE owner_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_notification_rules_owner ON notification_rules(owner_id);
