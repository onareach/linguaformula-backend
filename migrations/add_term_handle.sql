-- Add term_handle to tbl_term for stable, environment-independent lookups.
-- Run backfill_term_formula_handles.py after this to populate existing rows.

ALTER TABLE tbl_term ADD COLUMN IF NOT EXISTS term_handle VARCHAR(100) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tbl_term_handle
  ON tbl_term(term_handle) WHERE term_handle IS NOT NULL;

COMMENT ON COLUMN tbl_term.term_handle IS 'Unique slug for cross-environment import (e.g. statistics, population).';
