-- Beta feedback submissions for Lingua Formula.
-- Run after add_user_table.sql

CREATE TABLE IF NOT EXISTS tbl_feedback (
  feedback_id     UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_id         INTEGER NULL REFERENCES tbl_user(user_id),
  user_email      VARCHAR(255) NULL,
  course_context  INTEGER NULL,
  page_url        VARCHAR(2048) NULL,
  user_agent      TEXT NULL,
  viewport_width  INTEGER NULL,
  viewport_height INTEGER NULL,
  app_version     VARCHAR(128) NULL,
  feedback_type   VARCHAR(64) NULL,
  message         TEXT NOT NULL,
  cc_user         BOOLEAN NOT NULL DEFAULT false,
  reward_opt_in   BOOLEAN NOT NULL DEFAULT false,
  reward_contact  TEXT NULL,
  reward_handle   TEXT NULL,
  status          VARCHAR(32) NOT NULL DEFAULT 'new',
  admin_notes     TEXT NULL,
  screenshot_path VARCHAR(1024) NULL,
  CONSTRAINT tbl_feedback_status_check CHECK (status IN ('new', 'triaged', 'in_progress', 'resolved', 'reward_sent'))
);

CREATE INDEX IF NOT EXISTS idx_tbl_feedback_created_at ON tbl_feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tbl_feedback_user_id ON tbl_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_tbl_feedback_user_created ON tbl_feedback(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tbl_feedback_status ON tbl_feedback(status);

COMMENT ON TABLE tbl_feedback IS 'Beta user feedback submissions; used for tracking and reward fulfillment.';
