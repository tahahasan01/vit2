-- ═══════════════════════════════════════════════════════
-- Supabase SQL Schema — The Dirty Laundry V2
-- Run this in Supabase Dashboard → SQL Editor
-- ═══════════════════════════════════════════════════════

-- ── User Profiles (extends Supabase auth.users) ─────
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    consent_given BOOLEAN DEFAULT FALSE,
    privacy_acknowledged BOOLEAN DEFAULT FALSE,
    consent_given_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = id);

-- ── Garment Catalog ─────────────────────────────────
CREATE TABLE IF NOT EXISTS garments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'upper_body'
        CHECK (category IN ('upper_body', 'lower_body', 'dresses')),
    brand TEXT DEFAULT '',
    description TEXT DEFAULT '',
    image_url TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE garments ENABLE ROW LEVEL SECURITY;

-- Public read access (catalog is public)
CREATE POLICY "Anyone can read garments"
    ON garments FOR SELECT
    USING (TRUE);

-- ── Try-On Jobs ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS tryon_jobs (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    garment_id TEXT NOT NULL REFERENCES garments(id),
    category TEXT NOT NULL DEFAULT 'upper_body',
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'body_estimation', 'garment_synthesis', 'video_rendering', 'completed', 'failed')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    current_step TEXT DEFAULT 'upload',
    result_photo_url TEXT,
    result_video_url TEXT,
    result_mesh_url TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE tryon_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own jobs"
    ON tryon_jobs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own jobs"
    ON tryon_jobs FOR DELETE
    USING (auth.uid() = user_id);

-- Index for job history queries
CREATE INDEX IF NOT EXISTS idx_tryon_jobs_user_status
    ON tryon_jobs(user_id, status, created_at DESC);

-- ── Enable Realtime for job status push ─────────────
-- This allows the frontend to subscribe to job status changes
-- via Supabase Realtime instead of polling.
ALTER PUBLICATION supabase_realtime ADD TABLE tryon_jobs;

-- ── Storage Buckets (created via API, but documenting here) ─
-- avatars       (private)  — base avatar .glb files
-- garments      (public)   — garment product images
-- tryon-results (private)  — VTO photos, videos, meshes
-- user-uploads  (private)  — user selfie/fullbody photos
