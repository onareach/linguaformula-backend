-- Add optional segment classification to course-formula links (chapter, module, examination).
-- Run after add_institution_course_tables.sql.

ALTER TABLE tbl_user_course_formula
  ADD COLUMN IF NOT EXISTS segment_type VARCHAR(20) NULL,
  ADD COLUMN IF NOT EXISTS segment_label VARCHAR(255) NULL;

COMMENT ON COLUMN tbl_user_course_formula.segment_type IS 'Optional: chapter, module, or examination';
COMMENT ON COLUMN tbl_user_course_formula.segment_label IS 'Optional: e.g. Chapter 3, Midterm 1';
