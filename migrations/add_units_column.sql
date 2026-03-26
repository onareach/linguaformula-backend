-- Migration: Add units column to tbl_formula
-- Date: 2026-02-03

BEGIN;

-- Add units column (TEXT, nullable)
ALTER TABLE tbl_formula 
ADD COLUMN IF NOT EXISTS units TEXT;

COMMIT;

-- Verification query (uncomment to run after migration)
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'tbl_formula' 
--   AND column_name = 'units';
