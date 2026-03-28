-- Align tbl_lesson_block.media_asset_id with media_assets (BIGINT + FK + index).
-- Requires media_assets from add_media_library_v1.sql.

ALTER TABLE tbl_lesson_block
  ALTER COLUMN media_asset_id TYPE BIGINT USING media_asset_id::bigint;

ALTER TABLE tbl_lesson_block
  ADD CONSTRAINT tbl_lesson_block_media_asset_fkey
  FOREIGN KEY (media_asset_id) REFERENCES media_assets (media_asset_id)
  ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_tbl_lesson_block_media_asset_id
  ON tbl_lesson_block (media_asset_id)
  WHERE media_asset_id IS NOT NULL;
