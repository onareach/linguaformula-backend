-- Migration: Add is_admin column to tbl_user
-- Run after backup.

ALTER TABLE tbl_user ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;

-- Set onareach@yahoo.com as admin
UPDATE tbl_user SET is_admin = true WHERE email = 'onareach@yahoo.com';

COMMENT ON COLUMN tbl_user.is_admin IS 'Whether the user has admin privileges (e.g. manage formulas, view all users).';
