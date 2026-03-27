-- Media Library V1: folders + image assets (Postgres metadata, Vercel Blob storage)

CREATE TABLE IF NOT EXISTS media_folders (
  media_folder_id BIGSERIAL PRIMARY KEY,
  parent_media_folder_id BIGINT REFERENCES media_folders(media_folder_id) ON DELETE CASCADE,
  folder_name TEXT NOT NULL,
  folder_slug TEXT NOT NULL,
  folder_path TEXT NOT NULL UNIQUE,
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(parent_media_folder_id, folder_slug)
);

CREATE TABLE IF NOT EXISTS media_assets (
  media_asset_id BIGSERIAL PRIMARY KEY,
  media_folder_id BIGINT REFERENCES media_folders(media_folder_id) ON DELETE SET NULL,
  media_type TEXT NOT NULL CHECK (media_type = 'image'),
  original_filename TEXT NOT NULL,
  stored_filename TEXT NOT NULL,
  blob_pathname TEXT NOT NULL UNIQUE,
  blob_url TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  width_px INTEGER,
  height_px INTEGER,
  alt_text TEXT,
  title TEXT,
  uploaded_by_user_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_media_assets_media_folder_id ON media_assets(media_folder_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_created_at ON media_assets(created_at DESC);
