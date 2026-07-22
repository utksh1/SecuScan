-- Migration: 009_add_saved_views_owner_id
-- Closes issue #1743: the saved_views table had no owner_id column at all,
-- and the API layer performed no authentication or ownership checks, so any
-- caller could list, rename, overwrite, or delete every user's saved views.
--
-- This migration:
--   1. Adds an owner_id column (defaulting existing rows to 'default', the
--      same convention used for tasks/reports/workflows/etc).
--   2. Recreates the table to replace the old UNIQUE(name) constraint with
--      UNIQUE(owner_id, name) — two different owners may now reuse the same
--      view name, matching how workflows/credential_vault were migrated.
--   3. Rebuilds the supporting index scoped by owner.
--
-- The API layer (saved_views.py) now requires authentication and scopes
-- every query by the resolved owner_id.

ALTER TABLE saved_views ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'default';

CREATE TABLE saved_views_new (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL DEFAULT 'default',
    name        TEXT NOT NULL,
    filter_json TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at  TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    UNIQUE(owner_id, name)
);

INSERT INTO saved_views_new (id, owner_id, name, filter_json, created_at, updated_at)
SELECT id, COALESCE(owner_id, 'default'), name, filter_json, created_at, updated_at
FROM saved_views;

DROP TABLE saved_views;
ALTER TABLE saved_views_new RENAME TO saved_views;

DROP INDEX IF EXISTS idx_saved_views_name;
CREATE INDEX IF NOT EXISTS idx_saved_views_owner_name ON saved_views(owner_id, LOWER(name));