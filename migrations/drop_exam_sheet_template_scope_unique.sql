-- Allow multiple exam-sheet templates per course+segment again (variants/custom sheets).
-- add_segment_table_and_replace_segment_label.sql re-created the unique index
-- idx_exam_sheet_template_scope, which prevents creating custom sheets from an existing
-- template for the same course+segment. Drop it so "Create and edit" custom sheet works.

DROP INDEX IF EXISTS idx_exam_sheet_template_scope;
