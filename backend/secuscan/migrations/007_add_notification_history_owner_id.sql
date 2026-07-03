-- Migration: 007_add_notification_history_owner_id
-- Adds owner_id column to notification_history and an index so that
-- list queries can be scoped to the current user via a JOIN on
-- notification_rules.owner_id (closing the BOLA gap, issue #1483).
--
-- The column is added idempotently in database.py (_create_schema) using
-- PRAGMA table_info checks.  This file handles the backfill for any rows
-- left with a NULL owner_id, and creates the lookup index.

UPDATE notification_history
SET owner_id = (SELECT nr.owner_id FROM notification_rules nr WHERE nr.id = notification_history.rule_id)
WHERE owner_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_notification_history_owner ON notification_history(owner_id);
