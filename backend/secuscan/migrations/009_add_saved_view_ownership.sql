-- Migration: 009_add_saved_view_ownership
-- Adds owner_id scoping and a shared flag to saved_views.
--
-- owner_id prevents cross-user IDOR: user A cannot modify/delete user B's
-- private view.  The shared flag lets teams publish views as read-only to
-- other users without exposing mutation.
--
-- Backward-compatible: existing rows get owner_id = 'default' which
-- matches the DEFAULT_OWNER_ID constant in auth.py.
--
-- NOTE: The original table had UNIQUE(name).  Ownership scoping requires
-- per-owner uniqueness instead (same name allowed across owners), so we
-- recreate the table without the global UNIQUE constraint.

CREATE TABLE saved_views_new (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    filter_json TEXT NOT NULL,
    owner_id   TEXT NOT NULL DEFAULT 'default',
    shared     INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO saved_views_new (id, name, filter_json, created_at, updated_at)
    SELECT id, name, filter_json, created_at, updated_at
    FROM saved_views;

DROP TABLE saved_views;

ALTER TABLE saved_views_new RENAME TO saved_views;

CREATE INDEX idx_saved_views_owner_id ON saved_views(owner_id);
CREATE INDEX idx_saved_views_shared ON saved_views(shared);
