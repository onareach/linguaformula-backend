-- Add formula_handle to tbl_formula for stable, environment-independent lookups.
-- Run backfill_term_formula_handles.py after this to populate existing rows.

ALTER TABLE tbl_formula ADD COLUMN IF NOT EXISTS formula_handle VARCHAR(100) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tbl_formula_handle
  ON tbl_formula(formula_handle) WHERE formula_handle IS NOT NULL;

COMMENT ON COLUMN tbl_formula.formula_handle IS 'Unique slug for cross-environment import (e.g. discrete_mean, newtons_second_law).';
