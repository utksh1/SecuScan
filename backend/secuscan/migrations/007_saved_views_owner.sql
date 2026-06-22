-- Migration: 007_saved_views_owner
-- Adds owner_id logic to saved_views for BOLA prevention.
--
-- The schema changes and backfills are handled safely in database.py
-- so this script acts as a defensive pass over the data ensuring
-- all existing views have an owner and the proper index exists.

UPDATE saved_views SET owner_id = 'default' WHERE owner_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_saved_views_owner ON saved_views(owner_id);
