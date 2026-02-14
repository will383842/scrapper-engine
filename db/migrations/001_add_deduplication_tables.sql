-- ============================================================
-- MIGRATION: Add Ultra-Professional Deduplication Tables
-- ============================================================
-- Version: 1.0.0
-- Date: 2025-02-13
-- Description: Add multi-layer deduplication system tables
-- ============================================================

BEGIN;

-- ────────────────────────────────────────────────────────────
-- 1. URL Deduplication Cache
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS url_deduplication_cache (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    dedup_type VARCHAR(20) NOT NULL CHECK (dedup_type IN ('exact', 'normalized')),
    job_id INTEGER REFERENCES scraping_jobs(id) ON DELETE CASCADE,
    seen_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    UNIQUE (url, dedup_type, COALESCE(job_id, -1))
);

CREATE INDEX IF NOT EXISTS idx_url_dedup_url ON url_deduplication_cache(url);
CREATE INDEX IF NOT EXISTS idx_url_dedup_type ON url_deduplication_cache(dedup_type);
CREATE INDEX IF NOT EXISTS idx_url_dedup_job_id ON url_deduplication_cache(job_id) WHERE job_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_url_dedup_expires ON url_deduplication_cache(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_url_dedup_seen_at ON url_deduplication_cache(seen_at DESC);

COMMENT ON TABLE url_deduplication_cache IS 'Cache for URL deduplication (exact and normalized)';
COMMENT ON COLUMN url_deduplication_cache.dedup_type IS 'Type: exact (exact match) or normalized (http/https, www, etc.)';
COMMENT ON COLUMN url_deduplication_cache.expires_at IS 'TTL for temporal deduplication (NULL = never expires)';

-- ────────────────────────────────────────────────────────────
-- 2. Content Hash Cache
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS content_hash_cache (
    id SERIAL PRIMARY KEY,
    content_hash VARCHAR(64) NOT NULL,
    job_id INTEGER REFERENCES scraping_jobs(id) ON DELETE CASCADE,
    seen_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    sample_url TEXT,
    UNIQUE (content_hash, COALESCE(job_id, -1))
);

CREATE INDEX IF NOT EXISTS idx_content_hash ON content_hash_cache(content_hash);
CREATE INDEX IF NOT EXISTS idx_content_hash_job_id ON content_hash_cache(job_id) WHERE job_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_content_hash_expires ON content_hash_cache(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_content_hash_seen_at ON content_hash_cache(seen_at DESC);

COMMENT ON TABLE content_hash_cache IS 'Cache for content hash deduplication (detect similar pages)';
COMMENT ON COLUMN content_hash_cache.content_hash IS 'SHA256 hash of normalized page content';
COMMENT ON COLUMN content_hash_cache.sample_url IS 'Sample URL where this content was found (for debugging)';

-- ────────────────────────────────────────────────────────────
-- 3. Add content_hash column to scraped_contacts (optional)
-- ────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'scraped_contacts' AND column_name = 'content_hash'
    ) THEN
        ALTER TABLE scraped_contacts ADD COLUMN content_hash VARCHAR(64);
        CREATE INDEX idx_scraped_contacts_content_hash ON scraped_contacts(content_hash) WHERE content_hash IS NOT NULL;
        COMMENT ON COLUMN scraped_contacts.content_hash IS 'SHA256 hash of page content (for deduplication)';
    END IF;
END $$;

-- ────────────────────────────────────────────────────────────
-- 4. Cleanup Function (for expired entries)
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION cleanup_expired_deduplication_cache()
RETURNS TABLE(
    url_deleted BIGINT,
    content_deleted BIGINT
) AS $$
DECLARE
    url_count BIGINT;
    content_count BIGINT;
BEGIN
    -- Delete expired URL cache
    DELETE FROM url_deduplication_cache WHERE expires_at IS NOT NULL AND expires_at < NOW();
    GET DIAGNOSTICS url_count = ROW_COUNT;

    -- Delete expired content hash cache
    DELETE FROM content_hash_cache WHERE expires_at IS NOT NULL AND expires_at < NOW();
    GET DIAGNOSTICS content_count = ROW_COUNT;

    RETURN QUERY SELECT url_count, content_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_deduplication_cache() IS 'Delete expired deduplication cache entries (called by cron job)';

-- ────────────────────────────────────────────────────────────
-- 5. Statistics View (for dashboard)
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW deduplication_stats AS
SELECT
    (SELECT COUNT(*) FROM url_deduplication_cache WHERE dedup_type = 'exact') AS url_exact_count,
    (SELECT COUNT(*) FROM url_deduplication_cache WHERE dedup_type = 'normalized') AS url_normalized_count,
    (SELECT COUNT(DISTINCT email) FROM scraped_contacts) AS email_unique_count,
    (SELECT COUNT(*) FROM content_hash_cache) AS content_hash_count,
    (SELECT COUNT(*) FROM url_deduplication_cache WHERE expires_at IS NOT NULL AND expires_at < NOW()) AS expired_url_count,
    (SELECT COUNT(*) FROM content_hash_cache WHERE expires_at IS NOT NULL AND expires_at < NOW()) AS expired_content_count,
    (SELECT COUNT(*) FROM scraped_contacts) AS total_scraped_count,
    (SELECT
        ROUND(
            (COUNT(*) FILTER (WHERE expires_at IS NOT NULL AND expires_at > NOW())::NUMERIC / NULLIF(COUNT(*), 0)) * 100,
            2
        )
     FROM url_deduplication_cache) AS url_cache_hit_rate_pct,
    NOW() AS calculated_at;

COMMENT ON VIEW deduplication_stats IS 'Real-time deduplication statistics for dashboard';

-- ────────────────────────────────────────────────────────────
-- 6. Migration Metadata
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    applied_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO schema_migrations (version, description)
VALUES ('001', 'Add ultra-professional deduplication tables')
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- ────────────────────────────────────────────────────────────
-- 7. Grant Permissions (adjust as needed)
-- ────────────────────────────────────────────────────────────

-- GRANT SELECT, INSERT, UPDATE, DELETE ON url_deduplication_cache TO scraper_admin;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON content_hash_cache TO scraper_admin;
-- GRANT SELECT ON deduplication_stats TO scraper_admin;
-- GRANT USAGE, SELECT ON SEQUENCE url_deduplication_cache_id_seq TO scraper_admin;
-- GRANT USAGE, SELECT ON SEQUENCE content_hash_cache_id_seq TO scraper_admin;

-- ────────────────────────────────────────────────────────────
-- MIGRATION COMPLETE
-- ────────────────────────────────────────────────────────────

SELECT 'Migration 001 completed successfully!' AS status;
SELECT * FROM deduplication_stats;
