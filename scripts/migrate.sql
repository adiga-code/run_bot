-- Migration: add new onboarding fields
-- Run once on the existing database

ALTER TABLE users ADD COLUMN IF NOT EXISTS q_runs VARCHAR(10);
ALTER TABLE users ADD COLUMN IF NOT EXISTS q_structure VARCHAR(10);

-- Existing users already active — their status is already set correctly via server_default
-- New columns are nullable so existing rows are unaffected

-- Migration: add stress_level to session_logs
ALTER TABLE session_logs ADD COLUMN IF NOT EXISTS stress_level INTEGER;
