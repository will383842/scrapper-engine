-- ============================================================
-- SCRAPER-PRO : Schema PostgreSQL
-- ============================================================

-- Jobs de scraping
CREATE TABLE scraping_jobs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'google_search', 'google_maps', 'custom_urls'
    config JSONB NOT NULL,
    default_category VARCHAR(50),      -- 'avocat', 'blogueur', etc.
    default_platform VARCHAR(20),      -- 'sos-expat', 'ulixai'
    default_tags JSONB DEFAULT '[]',
    auto_inject_mailwizz BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, paused, completed, failed
    progress DECIMAL(5,2) DEFAULT 0.00,
    pages_scraped INTEGER DEFAULT 0,
    contacts_extracted INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    -- Checkpoint / resume support
    checkpoint_data JSONB DEFAULT '{}',
    -- For google_search/maps: {"last_page": 30, "results_collected": 45}
    -- For custom_urls: {"completed_urls": ["url1","url2"], "current_index": 3}
    resumed_from_job_id INTEGER,
    resume_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_status ON scraping_jobs(status);
CREATE INDEX idx_jobs_created_at ON scraping_jobs(created_at DESC);

-- Contacts bruts scrapes
CREATE TABLE scraped_contacts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    phone VARCHAR(50),
    website VARCHAR(500),
    address TEXT,
    social_media JSONB DEFAULT '{}',
    source_type VARCHAR(50),
    source_url TEXT,
    domain VARCHAR(255),
    country VARCHAR(5),
    keywords TEXT,
    job_id INTEGER REFERENCES scraping_jobs(id) ON DELETE SET NULL,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(30) DEFAULT 'pending_validation',
    -- pending_validation, validated, rejected, sent_to_mailwizz
    processed_at TIMESTAMPTZ
);

CREATE INDEX idx_scraped_status ON scraped_contacts(status);
CREATE INDEX idx_scraped_email ON scraped_contacts(email);
CREATE INDEX idx_scraped_job_id ON scraped_contacts(job_id);
CREATE INDEX idx_scraped_at ON scraped_contacts(scraped_at DESC);

-- Contacts valides et categorises
CREATE TABLE validated_contacts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    phone VARCHAR(50),
    website VARCHAR(500),
    address TEXT,
    social_media JSONB DEFAULT '{}',
    category VARCHAR(50) NOT NULL,     -- 'avocat', 'assureur', 'blogueur', etc.
    platform VARCHAR(20) NOT NULL,     -- 'sos-expat', 'ulixai'
    country VARCHAR(5),
    tags JSONB DEFAULT '[]',
    email_valid BOOLEAN DEFAULT TRUE,
    phone_valid BOOLEAN DEFAULT FALSE,
    last_validated_at TIMESTAMPTZ DEFAULT NOW(),
    mailwizz_list_id INTEGER NOT NULL,
    mailwizz_template VARCHAR(100),
    status VARCHAR(30) DEFAULT 'ready_for_mailwizz',
    -- ready_for_mailwizz, sent_to_mailwizz, failed, bounced
    mailwizz_subscriber_id VARCHAR(100),
    sent_to_mailwizz_at TIMESTAMPTZ,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    source_id INTEGER REFERENCES scraped_contacts(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_validated_email ON validated_contacts(email);
CREATE INDEX idx_validated_status ON validated_contacts(status);
CREATE INDEX idx_validated_platform ON validated_contacts(platform);
CREATE INDEX idx_validated_category ON validated_contacts(category);
CREATE INDEX idx_validated_mailwizz_list ON validated_contacts(mailwizz_list_id);

-- Log de synchronisation MailWizz
CREATE TABLE mailwizz_sync_log (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES validated_contacts(id) ON DELETE CASCADE,
    platform VARCHAR(20),
    list_id INTEGER,
    status VARCHAR(20),  -- success, failed
    response JSONB,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sync_contact ON mailwizz_sync_log(contact_id);
CREATE INDEX idx_sync_status ON mailwizz_sync_log(status);

-- Stats proxies
CREATE TABLE proxy_stats (
    id SERIAL PRIMARY KEY,
    proxy_url VARCHAR(500) UNIQUE NOT NULL,
    proxy_type VARCHAR(20),            -- 'datacenter', 'residential'
    provider VARCHAR(50),
    country VARCHAR(5),
    status VARCHAR(20) DEFAULT 'active',  -- active, cooldown, blacklisted
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 100.00,
    avg_response_ms INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    cooldown_until TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_proxy_status ON proxy_stats(status);

-- Cache anti-doublons URLs
CREATE TABLE url_fingerprints (
    id SERIAL PRIMARY KEY,
    url_normalized TEXT NOT NULL,
    url_hash VARCHAR(64) UNIQUE NOT NULL,
    content_hash VARCHAR(64),
    domain VARCHAR(255),
    spider_name VARCHAR(100),
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    visit_count INTEGER DEFAULT 1
);

CREATE INDEX idx_fingerprint_hash ON url_fingerprints(url_hash);
CREATE INDEX idx_fingerprint_domain ON url_fingerprints(domain);

-- Blacklist domaines email (bounce rate > 10%)
CREATE TABLE email_domain_blacklist (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    reason VARCHAR(100),
    bounce_count INTEGER DEFAULT 0,
    total_sent INTEGER DEFAULT 0,
    bounce_rate DECIMAL(5,2) DEFAULT 0.00,
    blacklisted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Logs erreurs
CREATE TABLE error_logs (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES scraping_jobs(id) ON DELETE SET NULL,
    error_type VARCHAR(100),
    error_message TEXT,
    url TEXT,
    proxy_used VARCHAR(255),
    stack_trace TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_errors_job ON error_logs(job_id);
CREATE INDEX idx_errors_created ON error_logs(created_at DESC);

-- WHOIS domain intelligence
CREATE TABLE whois_cache (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    registrar VARCHAR(255),
    registrar_url VARCHAR(500),
    creation_date TIMESTAMPTZ,
    expiration_date TIMESTAMPTZ,
    updated_date TIMESTAMPTZ,
    whois_private BOOLEAN DEFAULT FALSE,
    cloudflare_protected BOOLEAN DEFAULT FALSE,
    registrant_name VARCHAR(255),
    registrant_org VARCHAR(255),
    registrant_email VARCHAR(255),
    registrant_country VARCHAR(5),
    name_servers JSONB DEFAULT '[]',
    raw_whois TEXT,
    lookup_status VARCHAR(20) DEFAULT 'success',
    looked_up_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_whois_domain ON whois_cache(domain);
CREATE INDEX idx_whois_registrar ON whois_cache(registrar);

-- Articles de blog scrapes
CREATE TABLE scraped_articles (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES scraping_jobs(id) ON DELETE SET NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    content_text TEXT,
    content_html TEXT,
    excerpt TEXT,
    author TEXT,
    date_published TIMESTAMPTZ,
    categories TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    external_links JSONB DEFAULT '[]',
    internal_links JSONB DEFAULT '[]',
    featured_image_url TEXT,
    meta_description TEXT,
    word_count INTEGER DEFAULT 0,
    language VARCHAR(10),
    domain TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_articles_job_id ON scraped_articles(job_id);
CREATE INDEX idx_articles_domain ON scraped_articles(domain);
CREATE INDEX idx_articles_scraped_at ON scraped_articles(scraped_at DESC);
CREATE INDEX idx_articles_language ON scraped_articles(language);
