-- Migration: Rename formula table, rename id column, add symbolic_verbalization, and create discipline tables
-- This is a major schema change - run with caution and backup first!
-- 
-- Changes:
-- 1. Rename 'formula' table to 'tbl_formula'
-- 2. Rename 'id' column to 'formula_id' in tbl_formula
-- 3. Add 'symbolic_verbalization' column to tbl_formula
-- 4. Create 'tbl_disciplines' table
-- 5. Create 'tbl_formula_disciplines' linking table
-- 6. Update all foreign key references

-- ============================================================================
-- STEP 1: Add symbolic_verbalization column to formula table (before rename)
-- ============================================================================

ALTER TABLE formula 
ADD COLUMN IF NOT EXISTS symbolic_verbalization TEXT;

-- ============================================================================
-- STEP 2: Rename the formula table to tbl_formula
-- ============================================================================

ALTER TABLE formula RENAME TO tbl_formula;

-- ============================================================================
-- STEP 3: Rename the id column to formula_id in tbl_formula
-- ============================================================================

-- First, rename the sequence
ALTER SEQUENCE formula_id_seq RENAME TO tbl_formula_formula_id_seq;

-- Rename the column
ALTER TABLE tbl_formula RENAME COLUMN id TO formula_id;

-- Update the sequence owner
ALTER SEQUENCE tbl_formula_formula_id_seq OWNED BY tbl_formula.formula_id;

-- Set the default value for the column to use the renamed sequence
ALTER TABLE tbl_formula ALTER COLUMN formula_id SET DEFAULT nextval('tbl_formula_formula_id_seq'::regclass);

-- ============================================================================
-- STEP 4: Update all foreign key references to use new table/column names
-- ============================================================================

-- Update application_formula table
ALTER TABLE application_formula 
  DROP CONSTRAINT IF EXISTS application_formula_formula_id_fkey;

ALTER TABLE application_formula 
  ADD CONSTRAINT application_formula_formula_id_fkey 
  FOREIGN KEY (formula_id) REFERENCES tbl_formula(formula_id) ON DELETE CASCADE;

-- Update formula_variables table (if it exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'formula_variables') THEN
    ALTER TABLE formula_variables 
      DROP CONSTRAINT IF EXISTS formula_variables_formula_id_fkey;
    
    ALTER TABLE formula_variables 
      ADD CONSTRAINT formula_variables_formula_id_fkey 
      FOREIGN KEY (formula_id) REFERENCES tbl_formula(formula_id) ON DELETE CASCADE;
  END IF;
END $$;

-- Update formula_relationships table (if it exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'formula_relationships') THEN
    ALTER TABLE formula_relationships 
      DROP CONSTRAINT IF EXISTS formula_relationships_main_formula_id_fkey;
    
    ALTER TABLE formula_relationships 
      DROP CONSTRAINT IF EXISTS formula_relationships_helper_formula_id_fkey;
    
    ALTER TABLE formula_relationships 
      ADD CONSTRAINT formula_relationships_main_formula_id_fkey 
      FOREIGN KEY (main_formula_id) REFERENCES tbl_formula(formula_id) ON DELETE CASCADE;
    
    ALTER TABLE formula_relationships 
      ADD CONSTRAINT formula_relationships_helper_formula_id_fkey 
      FOREIGN KEY (helper_formula_id) REFERENCES tbl_formula(formula_id) ON DELETE CASCADE;
  END IF;
END $$;

-- Update formula_keywords table (if it exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'formula_keywords') THEN
    ALTER TABLE formula_keywords 
      DROP CONSTRAINT IF EXISTS formula_keywords_formula_id_fkey;
    
    ALTER TABLE formula_keywords 
      ADD CONSTRAINT formula_keywords_formula_id_fkey 
      FOREIGN KEY (formula_id) REFERENCES tbl_formula(formula_id) ON DELETE CASCADE;
  END IF;
END $$;

-- Update formula_examples table (if it exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'formula_examples') THEN
    ALTER TABLE formula_examples 
      DROP CONSTRAINT IF EXISTS formula_examples_formula_id_fkey;
    
    ALTER TABLE formula_examples 
      ADD CONSTRAINT formula_examples_formula_id_fkey 
      FOREIGN KEY (formula_id) REFERENCES tbl_formula(formula_id) ON DELETE CASCADE;
  END IF;
END $$;

-- Update formula_prerequisites table (if it exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'formula_prerequisites') THEN
    ALTER TABLE formula_prerequisites 
      DROP CONSTRAINT IF EXISTS formula_prerequisites_formula_id_fkey;
    
    ALTER TABLE formula_prerequisites 
      ADD CONSTRAINT formula_prerequisites_formula_id_fkey 
      FOREIGN KEY (formula_id) REFERENCES tbl_formula(formula_id) ON DELETE CASCADE;
  END IF;
END $$;

-- ============================================================================
-- STEP 5: Update indexes to use new table/column names
-- ============================================================================

-- Drop old indexes
DROP INDEX IF EXISTS idx_formula_display_order;
DROP INDEX IF EXISTS idx_formula_name;
DROP INDEX IF EXISTS idx_application_formula_formula_id;

-- Create new indexes with updated names
CREATE INDEX IF NOT EXISTS idx_tbl_formula_display_order ON tbl_formula(display_order);
CREATE INDEX IF NOT EXISTS idx_tbl_formula_name ON tbl_formula(formula_name);
CREATE INDEX IF NOT EXISTS idx_application_formula_formula_id ON application_formula(formula_id);

-- ============================================================================
-- STEP 6: Create tbl_disciplines table
-- ============================================================================

CREATE TABLE IF NOT EXISTS tbl_disciplines (
    discipline_id SERIAL PRIMARY KEY,
    discipline_name VARCHAR(200) NOT NULL,
    discipline_handle VARCHAR(100) NOT NULL UNIQUE,
    discipline_description TEXT,
    discipline_parent_id INTEGER REFERENCES tbl_disciplines(discipline_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on discipline_handle for fast lookups
CREATE INDEX IF NOT EXISTS idx_tbl_disciplines_handle ON tbl_disciplines(discipline_handle);

-- Create index on discipline_parent_id for hierarchy queries
CREATE INDEX IF NOT EXISTS idx_tbl_disciplines_parent_id ON tbl_disciplines(discipline_parent_id);

-- ============================================================================
-- STEP 7: Create tbl_formula_disciplines linking table
-- ============================================================================

CREATE TABLE IF NOT EXISTS tbl_formula_disciplines (
    formula_discipline_id SERIAL PRIMARY KEY,
    formula_id INTEGER NOT NULL REFERENCES tbl_formula(formula_id) ON DELETE CASCADE,
    discipline_id INTEGER NOT NULL REFERENCES tbl_disciplines(discipline_id) ON DELETE CASCADE,
    formula_discipline_is_primary BOOLEAN NOT NULL DEFAULT false,
    formula_discipline_rank INTEGER,
    formula_discipline_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Ensure a formula-discipline combination is unique
    UNIQUE(formula_id, discipline_id)
);

-- Create a partial unique index to ensure only one primary discipline per formula
CREATE UNIQUE INDEX IF NOT EXISTS idx_tbl_formula_disciplines_one_primary 
  ON tbl_formula_disciplines(formula_id) 
  WHERE formula_discipline_is_primary = true;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tbl_formula_disciplines_formula_id ON tbl_formula_disciplines(formula_id);
CREATE INDEX IF NOT EXISTS idx_tbl_formula_disciplines_discipline_id ON tbl_formula_disciplines(discipline_id);

-- ============================================================================
-- STEP 8: Update table comments
-- ============================================================================

COMMENT ON TABLE tbl_formula IS 'Core table storing mathematical formulas with LaTeX and English descriptions';
COMMENT ON TABLE tbl_disciplines IS 'Disciplines/subject areas that formulas belong to (e.g., Classical Mechanics, Thermodynamics)';
COMMENT ON TABLE tbl_formula_disciplines IS 'Many-to-many relationship between formulas and disciplines with primary/rank information';

-- ============================================================================
-- VERIFICATION QUERIES (uncomment to run after migration)
-- ============================================================================

-- Verify table rename
-- SELECT table_name FROM information_schema.tables WHERE table_name = 'tbl_formula';

-- Verify column rename
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'tbl_formula' AND column_name = 'formula_id';

-- Verify new column exists
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'tbl_formula' AND column_name = 'symbolic_verbalization';

-- Verify new tables exist
-- SELECT table_name FROM information_schema.tables WHERE table_name IN ('tbl_disciplines', 'tbl_formula_disciplines');
