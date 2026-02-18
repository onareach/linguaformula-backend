-- Add formulaic_expression column to tbl_term.
-- Stores LaTeX or symbol representation (e.g. A \cup B for "union", N for "population size").
-- NULL for terms without a formulaic expression (e.g. "statistics").

ALTER TABLE tbl_term ADD COLUMN IF NOT EXISTS formulaic_expression TEXT NULL;
COMMENT ON COLUMN tbl_term.formulaic_expression IS 'LaTeX or symbol representation (e.g. A \\cup B, N). NULL if term has no formulaic expression.';
