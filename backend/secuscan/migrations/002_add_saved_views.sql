-- Migration: 002_add_saved_views
-- Adds the saved_views table for persisting named filter/sort/date presets
-- created by users on the Findings page.
--
-- Design notes:
--   - name is UNIQUE so the application-level 409 on duplicate names is
--     backed by a real database constraint.
--   - filter_json stores the serialised FilterPreset object; validated by
--     the API layer (Pydantic) before insert so the column is always valid.
--   - updated_at is maintained manually on PUT so callers can detect stale
--     local copies when merging localStorage with backend state.

CREATE TABLE IF NOT EXISTS saved_views (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    filter_json TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at  TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_saved_views_name ON saved_views(LOWER(name));
