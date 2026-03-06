-- Add catalog_course_id to tbl_exam_sheet_template for direct catalog lookup.
-- Templates for catalog courses can now be queried by catalog_course_id without joining through tbl_course.

ALTER TABLE tbl_exam_sheet_template
  ADD COLUMN IF NOT EXISTS catalog_course_id INTEGER NULL;

-- Backfill from course
UPDATE tbl_exam_sheet_template t
SET catalog_course_id = c.catalog_course_id
FROM tbl_course c
WHERE t.course_id = c.course_id
  AND t.catalog_course_id IS NULL
  AND c.catalog_course_id IS NOT NULL;

-- Index for catalog lookups
CREATE INDEX IF NOT EXISTS idx_exam_sheet_template_catalog
  ON tbl_exam_sheet_template(catalog_course_id)
  WHERE catalog_course_id IS NOT NULL;

-- FK (optional; allows NULL for user-created non-catalog templates)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'fk_exam_sheet_template_catalog'
      AND table_name = 'tbl_exam_sheet_template'
  ) THEN
    ALTER TABLE tbl_exam_sheet_template
      ADD CONSTRAINT fk_exam_sheet_template_catalog
      FOREIGN KEY (catalog_course_id) REFERENCES tbl_catalog_course(catalog_course_id) ON DELETE SET NULL;
  END IF;
END $$;

COMMENT ON COLUMN tbl_exam_sheet_template.catalog_course_id IS 'Catalog course this template belongs to; set when course has catalog_course_id. Enables direct lookup of pre-configured templates.';
