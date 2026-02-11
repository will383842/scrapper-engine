-- Migration 002: Add checkpoint/resume support to scraping_jobs
-- Run: psql -U scraper_admin -d scraper_db -f db/migrations/002_add_checkpoint_resume.sql

ALTER TABLE scraping_jobs
    ADD COLUMN IF NOT EXISTS checkpoint_data JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS resumed_from_job_id INTEGER,
    ADD COLUMN IF NOT EXISTS resume_count INTEGER DEFAULT 0;

-- Add index for finding resumable jobs
CREATE INDEX IF NOT EXISTS idx_jobs_checkpoint ON scraping_jobs(status)
    WHERE status IN ('failed', 'paused') AND checkpoint_data != '{}';
