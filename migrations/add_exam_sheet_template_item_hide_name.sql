-- Allow exam-sheet template items to print definition/formula only (no term/formula name).
ALTER TABLE tbl_exam_sheet_template_item
  ADD COLUMN IF NOT EXISTS hide_name BOOLEAN NOT NULL DEFAULT false;
