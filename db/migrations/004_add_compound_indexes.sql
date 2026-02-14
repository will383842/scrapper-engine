-- Migration 004: Add compound indexes for query performance
-- Run: psql -U scraper_admin -d scraper_db -f 004_add_compound_indexes.sql

-- process_contacts: batch fetch by status + scraped_at order
CREATE INDEX IF NOT EXISTS idx_scraped_status_scraped_at
    ON scraped_contacts(status, scraped_at ASC);

-- sync_to_mailwizz: batch fetch by status + retry_count + created_at order
CREATE INDEX IF NOT EXISTS idx_validated_status_retry_created
    ON validated_contacts(status, retry_count, created_at ASC);

-- sync_log: analytics queries by contact + status + time
CREATE INDEX IF NOT EXISTS idx_sync_contact_status
    ON mailwizz_sync_log(contact_id, status, synced_at DESC);

-- domain blacklist: lookup by domain with bounce_rate filter
CREATE INDEX IF NOT EXISTS idx_blacklist_domain_bounce
    ON email_domain_blacklist(domain, bounce_rate, bounce_count);
