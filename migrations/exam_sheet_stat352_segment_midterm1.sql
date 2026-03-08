-- Set segment_label = 'Midterm 1' for exam sheet templates connected to STAT 352
-- that currently have no segment. Ensures "Standard" sheet appears under STAT 352 + Midterm 1.

UPDATE tbl_exam_sheet_template
SET segment_label = 'Midterm 1'
WHERE (segment_label IS NULL OR TRIM(COALESCE(segment_label, '')) = '')
  AND (
    catalog_course_id = (
      SELECT catalog_course_id FROM tbl_catalog_course
      WHERE TRIM(COALESCE(course_code, '')) = 'STAT 352'
         OR course_name ILIKE '%STAT 352%'
      LIMIT 1
    )
    OR course_id IN (
      SELECT course_id FROM tbl_course
      WHERE catalog_course_id = (
        SELECT catalog_course_id FROM tbl_catalog_course
        WHERE TRIM(COALESCE(course_code, '')) = 'STAT 352'
           OR course_name ILIKE '%STAT 352%'
        LIMIT 1
      )
    )
  );
