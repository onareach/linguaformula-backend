-- Simplify course segment: remove segment_type, keep only segment (segment_label).
-- Courses now have a flat list of segments (e.g. Ch 1, Midterm 1) instead of type+label hierarchy.
-- Run after add_course_formula_segment.sql and add_user_course_term.sql.

ALTER TABLE tbl_user_course_formula
  DROP COLUMN IF EXISTS segment_type;

ALTER TABLE tbl_user_course_term
  DROP COLUMN IF EXISTS segment_type;
