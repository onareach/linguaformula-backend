-- Add source and parent_template_id to tbl_exam_sheet_template.
-- source: admin | catalog | variant | scratch
-- parent_template_id: FK for variant breadcrumb; NULL for others.

ALTER TABLE tbl_exam_sheet_template
  ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'admin';

ALTER TABLE tbl_exam_sheet_template
  ADD COLUMN IF NOT EXISTS parent_template_id INTEGER NULL;

-- Backfill: all existing rows default to 'admin'
UPDATE tbl_exam_sheet_template
SET source = 'admin'
WHERE source IS NULL OR source = '';

-- Add CHECK constraint for source
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'chk_exam_sheet_template_source'
      AND conrelid = 'tbl_exam_sheet_template'::regclass
  ) THEN
    ALTER TABLE tbl_exam_sheet_template
      ADD CONSTRAINT chk_exam_sheet_template_source
      CHECK (source IN ('admin', 'catalog', 'variant', 'scratch'));
  END IF;
END $$;

-- FK for parent_template_id
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'fk_exam_sheet_template_parent'
      AND table_name = 'tbl_exam_sheet_template'
  ) THEN
    ALTER TABLE tbl_exam_sheet_template
      ADD CONSTRAINT fk_exam_sheet_template_parent
      FOREIGN KEY (parent_template_id) REFERENCES tbl_exam_sheet_template(template_id) ON DELETE SET NULL;
  END IF;
END $$;

COMMENT ON COLUMN tbl_exam_sheet_template.source IS 'admin=created by admin on setup; catalog=user copy-to-course; variant=user Add variant; scratch=user from scratch';
COMMENT ON COLUMN tbl_exam_sheet_template.parent_template_id IS 'For variant: template this was copied from; NULL for admin/catalog/scratch';
