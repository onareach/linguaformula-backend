-- Require course+segment: assign segment 'Midterm 1' to all STAT 352 catalog course terms and formulas
-- that currently have no segment. Run after add_catalog_course_term_formula_tables.sql.

UPDATE tbl_catalog_course_term
SET segment_label = 'Midterm 1'
WHERE catalog_course_id = (
  SELECT catalog_course_id FROM tbl_catalog_course
  WHERE TRIM(COALESCE(course_code, '')) = 'STAT 352'
     OR course_name ILIKE '%STAT 352%'
  LIMIT 1
)
AND (segment_label IS NULL OR TRIM(COALESCE(segment_label, '')) = '');

UPDATE tbl_catalog_course_formula
SET segment_label = 'Midterm 1'
WHERE catalog_course_id = (
  SELECT catalog_course_id FROM tbl_catalog_course
  WHERE TRIM(COALESCE(course_code, '')) = 'STAT 352'
     OR course_name ILIKE '%STAT 352%'
  LIMIT 1
)
AND (segment_label IS NULL OR TRIM(COALESCE(segment_label, '')) = '');
