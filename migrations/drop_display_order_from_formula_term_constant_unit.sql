-- Drop display_order from tbl_formula, tbl_term, tbl_constant, tbl_unit
-- These columns are not used for ordering (API sorts by name). Removing them
-- simplifies JSON import (admin no longer needs to supply meaningless numbers).
-- display_order remains in tbl_question, tbl_question_answer, tbl_user_course_formula,
-- tbl_user_course_term where it is used for ordering.

BEGIN;

-- tbl_formula
DROP INDEX IF EXISTS idx_tbl_formula_display_order;
ALTER TABLE tbl_formula DROP COLUMN IF EXISTS display_order;

-- tbl_term
DROP INDEX IF EXISTS idx_tbl_term_display_order;
ALTER TABLE tbl_term DROP COLUMN IF EXISTS display_order;

-- tbl_constant
DROP INDEX IF EXISTS idx_tbl_constant_display_order;
ALTER TABLE tbl_constant DROP COLUMN IF EXISTS display_order;

-- tbl_unit
DROP INDEX IF EXISTS idx_tbl_unit_display_order;
ALTER TABLE tbl_unit DROP COLUMN IF EXISTS display_order;

COMMIT;
