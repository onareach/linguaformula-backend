-- Allow multiple exam-sheet templates per course+segment (variants).
-- Drop the unique constraint that enforced one template per scope.

DROP INDEX IF EXISTS idx_exam_sheet_template_scope;
