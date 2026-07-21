ALTER TABLE saved_views ADD COLUMN owner_id TEXT NOT NULL DEFAULT '';
ALTER TABLE saved_views ADD COLUMN shared    INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_saved_views_owner ON saved_views(owner_id);
