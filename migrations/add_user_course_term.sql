-- Add course-term linkage (parallel to tbl_user_course_formula).
-- Run after add_institution_course_tables.sql and add_course_formula_segment.sql.
-- User must be enrolled in course before adding terms.

CREATE TABLE IF NOT EXISTS tbl_user_course_term (
  user_id       INTEGER NOT NULL,
  course_id     INTEGER NOT NULL,
  term_id       INTEGER NOT NULL,
  display_order INTEGER NULL DEFAULT 0,
  segment_type  VARCHAR(20) NULL,
  segment_label VARCHAR(255) NULL,
  created_at    TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, course_id, term_id),
  CONSTRAINT tbl_user_course_term_enrollment_fkey
    FOREIGN KEY (user_id, course_id) REFERENCES tbl_user_course(user_id, course_id) ON DELETE CASCADE,
  CONSTRAINT tbl_user_course_term_term_fkey
    FOREIGN KEY (term_id) REFERENCES tbl_term(term_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tbl_user_course_term_user_course ON tbl_user_course_term(user_id, course_id);
CREATE INDEX IF NOT EXISTS idx_tbl_user_course_term_term ON tbl_user_course_term(term_id);

COMMENT ON TABLE tbl_user_course_term IS 'Terms linked to a user course; requires enrollment (tbl_user_course).';
COMMENT ON COLUMN tbl_user_course_term.segment_type IS 'Optional: chapter, module, or examination';
COMMENT ON COLUMN tbl_user_course_term.segment_label IS 'Optional: e.g. Chapter 3, Midterm 1';
