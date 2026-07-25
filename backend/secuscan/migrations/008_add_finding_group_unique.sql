-- Migration: 008_add_finding_group_unique
-- Replaces the non-unique index idx_findings_group_id with a UNIQUE
-- index on (owner_id, finding_group_id) so that the same vulnerability
-- found by different tasks does not produce duplicate rows.

BEGIN TRANSACTION;

-- Remove duplicates keeping the most recently discovered row per group
DELETE FROM findings WHERE rowid NOT IN (
    SELECT MIN(rowid) FROM findings
    WHERE owner_id IS NOT NULL AND finding_group_id IS NOT NULL
    GROUP BY owner_id, finding_group_id
);

DROP INDEX IF EXISTS idx_findings_group_id;
CREATE UNIQUE INDEX IF NOT EXISTS idx_findings_group_id ON findings(owner_id, finding_group_id);

COMMIT;
