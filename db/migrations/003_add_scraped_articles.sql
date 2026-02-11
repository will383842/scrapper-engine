-- Migration 003: Add scraped_articles table for blog content scraping
-- Date: 2026-02-11

CREATE TABLE IF NOT EXISTS scraped_articles (
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

CREATE INDEX IF NOT EXISTS idx_articles_job_id ON scraped_articles(job_id);
CREATE INDEX IF NOT EXISTS idx_articles_domain ON scraped_articles(domain);
CREATE INDEX IF NOT EXISTS idx_articles_scraped_at ON scraped_articles(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_language ON scraped_articles(language);
