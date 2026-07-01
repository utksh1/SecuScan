-- Migration: 007_add_schedule_timezone
-- Adds the schedule_timezone column to the workflows table.
--
-- Since SQLite does not support ALTER TABLE ADD COLUMN IF NOT EXISTS,
-- the column addition itself is implemented idempotently in Python inside
-- backend/secuscan/database.py (_create_schema) using PRAGMA table_info.
-- This ensures subsequent runs of database initialization do not raise errors.
--
-- This file acts as a placeholder to keep the migration timeline tracked.
SELECT 1;
