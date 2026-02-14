-- Migration 005: Add Expat.com specific fields to scraped_articles
-- Date: 2026-02-13

-- Add new columns for Expat.com geographical and categorical metadata
ALTER TABLE scraped_articles
ADD COLUMN IF NOT EXISTS country VARCHAR(100),
ADD COLUMN IF NOT EXISTS region VARCHAR(100),
ADD COLUMN IF NOT EXISTS city VARCHAR(100),
ADD COLUMN IF NOT EXISTS category_expat VARCHAR(100);

-- Create indexes for efficient querying by geographical data
CREATE INDEX IF NOT EXISTS idx_articles_country ON scraped_articles(country);
CREATE INDEX IF NOT EXISTS idx_articles_region ON scraped_articles(region);
CREATE INDEX IF NOT EXISTS idx_articles_city ON scraped_articles(city);
CREATE INDEX IF NOT EXISTS idx_articles_category_expat ON scraped_articles(category_expat);

-- Create composite index for common queries (country + category)
CREATE INDEX IF NOT EXISTS idx_articles_country_category ON scraped_articles(country, category_expat);

-- Add comment for documentation
COMMENT ON COLUMN scraped_articles.country IS 'Country extracted from Expat.com URL structure';
COMMENT ON COLUMN scraped_articles.region IS 'Geographical region (europe, asia, africa, americas, oceania)';
COMMENT ON COLUMN scraped_articles.city IS 'City name extracted from URL (optional)';
COMMENT ON COLUMN scraped_articles.category_expat IS 'Expat.com category (guide, forum, emploi, immobilier, etc.)';
