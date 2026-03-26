-- Migration: Add example and historical_context columns to tbl_formula
-- Date: 2026-02-03

BEGIN;

-- Add example column (TEXT, nullable)
ALTER TABLE tbl_formula 
ADD COLUMN IF NOT EXISTS example TEXT;

-- Add historical_context column (TEXT, nullable)
ALTER TABLE tbl_formula 
ADD COLUMN IF NOT EXISTS historical_context TEXT;

COMMIT;

-- Verification queries (uncomment to run after migration)
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'tbl_formula' 
--   AND column_name IN ('example', 'historical_context')
-- ORDER BY column_name;
