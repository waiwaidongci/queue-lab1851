-- Time-varying arrival intensity support (2026-11).
-- Fresh databases get this column from ORM metadata; existing databases apply:
ALTER TABLE arrival_profiles ADD COLUMN IF NOT EXISTS segments JSON;
-- NULL segments means a legacy constant-rate profile (old data stays compatible).
CREATE INDEX IF NOT EXISTS arrival_profile_study_idx ON arrival_profiles (study_id);
