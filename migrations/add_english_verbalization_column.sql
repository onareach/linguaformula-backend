-- Add english_verbalization column to formula table
-- Run with: heroku pg:psql -a my-physics-formula-viewer-3x -f migrations/add_english_verbalization_column.sql
-- Or locally: psql -d linguaformula -U dev_user -f migrations/add_english_verbalization_column.sql

-- Add the english_verbalization column
ALTER TABLE formula 
ADD COLUMN IF NOT EXISTS english_verbalization TEXT;

-- Verify the column was added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'formula' 
  AND column_name = 'english_verbalization';

-- Show current formula table structure
SELECT column_name, data_type, is_nullable, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'formula'
ORDER BY ordinal_position;
