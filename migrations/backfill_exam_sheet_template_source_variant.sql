-- Mark templates that were created as copies but wrongly have source='admin' as source='variant'
-- so they show as user custom (Edit link, excluded from admin exam-sheet list).
-- Run after add_exam_sheet_template_source.sql.

-- Copies: parent_template_id set (current create flow)
UPDATE tbl_exam_sheet_template
SET source = 'variant'
WHERE parent_template_id IS NOT NULL
  AND source = 'admin';

-- Fallback: name suggests user custom (e.g. "STAT 352 Midterm 1 DL Custom") but was stored as admin
UPDATE tbl_exam_sheet_template
SET source = 'variant'
WHERE source = 'admin'
  AND template_name ILIKE '% custom';
