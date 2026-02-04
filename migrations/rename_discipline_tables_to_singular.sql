-- Migration: Rename discipline tables to singular form
-- Changes:
-- 1. Rename 'tbl_disciplines' to 'tbl_discipline'
-- 2. Rename 'tbl_formula_disciplines' to 'tbl_formula_discipline'
-- 3. Update all foreign key references

-- ============================================================================
-- STEP 1: Rename tbl_disciplines to tbl_discipline
-- ============================================================================

ALTER TABLE IF EXISTS tbl_disciplines RENAME TO tbl_discipline;

-- ============================================================================
-- STEP 2: Update foreign key in tbl_discipline (self-reference for parent)
-- ============================================================================

-- Drop and recreate the self-referencing foreign key
ALTER TABLE tbl_discipline 
  DROP CONSTRAINT IF EXISTS tbl_disciplines_discipline_parent_id_fkey;

ALTER TABLE tbl_discipline 
  ADD CONSTRAINT tbl_discipline_discipline_parent_id_fkey 
  FOREIGN KEY (discipline_parent_id) REFERENCES tbl_discipline(discipline_id) ON DELETE SET NULL;

-- ============================================================================
-- STEP 3: Rename tbl_formula_disciplines to tbl_formula_discipline
-- ============================================================================

ALTER TABLE IF EXISTS tbl_formula_disciplines RENAME TO tbl_formula_discipline;

-- ============================================================================
-- STEP 4: Update foreign key references in tbl_formula_discipline
-- ============================================================================

-- Drop existing foreign keys
ALTER TABLE tbl_formula_discipline 
  DROP CONSTRAINT IF EXISTS tbl_formula_disciplines_formula_id_fkey;

ALTER TABLE tbl_formula_discipline 
  DROP CONSTRAINT IF EXISTS tbl_formula_disciplines_discipline_id_fkey;

-- Recreate foreign keys with new table names
ALTER TABLE tbl_formula_discipline 
  ADD CONSTRAINT tbl_formula_discipline_formula_id_fkey 
  FOREIGN KEY (formula_id) REFERENCES tbl_formula(formula_id) ON DELETE CASCADE;

ALTER TABLE tbl_formula_discipline 
  ADD CONSTRAINT tbl_formula_discipline_discipline_id_fkey 
  FOREIGN KEY (discipline_id) REFERENCES tbl_discipline(discipline_id) ON DELETE CASCADE;

-- ============================================================================
-- STEP 5: Update indexes
-- ============================================================================

-- Drop old indexes
DROP INDEX IF EXISTS idx_tbl_disciplines_handle;
DROP INDEX IF EXISTS idx_tbl_disciplines_parent_id;
DROP INDEX IF EXISTS idx_tbl_formula_disciplines_formula_id;
DROP INDEX IF EXISTS idx_tbl_formula_disciplines_discipline_id;
DROP INDEX IF EXISTS idx_tbl_formula_disciplines_one_primary;

-- Create new indexes with updated names
CREATE INDEX IF NOT EXISTS idx_tbl_discipline_handle ON tbl_discipline(discipline_handle);
CREATE INDEX IF NOT EXISTS idx_tbl_discipline_parent_id ON tbl_discipline(discipline_parent_id);
CREATE INDEX IF NOT EXISTS idx_tbl_formula_discipline_formula_id ON tbl_formula_discipline(formula_id);
CREATE INDEX IF NOT EXISTS idx_tbl_formula_discipline_discipline_id ON tbl_formula_discipline(discipline_id);

-- Create partial unique index for one primary discipline per formula
CREATE UNIQUE INDEX IF NOT EXISTS idx_tbl_formula_discipline_one_primary 
  ON tbl_formula_discipline(formula_id) 
  WHERE formula_discipline_is_primary = true;

-- ============================================================================
-- STEP 6: Update table comments
-- ============================================================================

COMMENT ON TABLE tbl_discipline IS 'Disciplines/subject areas that formulas belong to (e.g., Classical Mechanics, Thermodynamics)';
COMMENT ON TABLE tbl_formula_discipline IS 'Many-to-many relationship between formulas and disciplines with primary/rank information';

-- ============================================================================
-- VERIFICATION QUERIES (uncomment to run after migration)
-- ============================================================================

-- Verify table renames
-- SELECT table_name FROM information_schema.tables WHERE table_name IN ('tbl_discipline', 'tbl_formula_discipline');
