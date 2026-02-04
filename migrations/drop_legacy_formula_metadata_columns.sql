-- Drop legacy metadata columns from tbl_formula
-- These columns were introduced by an earlier "enhanced schema" concept but are no longer used
-- by the Lingua Formula app (disciplines-based organization is used instead).

BEGIN;

-- Drop indexes that depend on the legacy columns (safe if they don't exist)
DROP INDEX IF EXISTS idx_formula_category;
DROP INDEX IF EXISTS idx_formula_difficulty;

-- Drop the legacy columns (safe if they don't exist)
ALTER TABLE IF EXISTS tbl_formula DROP COLUMN IF EXISTS category;
ALTER TABLE IF EXISTS tbl_formula DROP COLUMN IF EXISTS difficulty_level;
ALTER TABLE IF EXISTS tbl_formula DROP COLUMN IF EXISTS assumptions;
ALTER TABLE IF EXISTS tbl_formula DROP COLUMN IF EXISTS output_target;

COMMIT;

