-- Add question_handle to tbl_question for stable, environment-independent lookups.
-- Run backfill_question_handles.py after this to populate existing rows.

ALTER TABLE tbl_question ADD COLUMN IF NOT EXISTS question_handle VARCHAR(120) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tbl_question_handle
  ON tbl_question(question_handle) WHERE question_handle IS NOT NULL;

COMMENT ON COLUMN tbl_question.question_handle IS 'Unique slug for cross-environment import (e.g. z_score_interpretation, sample_size_definition_mcq).';
