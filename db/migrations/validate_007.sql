-- Validation script for migration 007
-- Run after applying 007_add_metadata_columns.sql

-- Check that all columns exist
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'scraped_articles'
    AND column_name IN (
        'country', 'region', 'city',
        'extracted_category', 'extracted_subcategory',
        'year', 'month'
    )
ORDER BY column_name;

-- Expected output:
-- column_name             | data_type         | is_nullable
-- city                    | character varying | YES
-- country                 | character varying | YES
-- extracted_category      | character varying | YES
-- extracted_subcategory   | character varying | YES
-- month                   | integer           | YES
-- region                  | character varying | YES
-- year                    | integer           | YES

-- Check that all indexes exist
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'scraped_articles'
    AND indexname IN (
        'idx_articles_country',
        'idx_articles_region',
        'idx_articles_city',
        'idx_articles_category',
        'idx_articles_language',
        'idx_articles_year_month',
        'idx_articles_geo_category'
    )
ORDER BY indexname;

-- Expected output: 7 indexes

-- Check column comments
SELECT
    column_name,
    col_description((table_schema||'.'||table_name)::regclass::oid, ordinal_position) as comment
FROM information_schema.columns
WHERE table_name = 'scraped_articles'
    AND column_name IN (
        'country', 'region', 'city',
        'extracted_category', 'extracted_subcategory',
        'year', 'month'
    )
ORDER BY column_name;

-- Test insert with new columns
INSERT INTO scraped_articles
    (url, title, content_text, domain, word_count,
     country, region, city, extracted_category, year, month)
VALUES
    ('https://test.com/migration-007-test',
     'Test Article for Migration 007',
     'This is a test article to validate the new metadata columns.',
     'test.com',
     10,
     'france',
     'europe',
     'paris',
     'visa',
     2024,
     3)
ON CONFLICT (url) DO UPDATE SET
    country = EXCLUDED.country,
    region = EXCLUDED.region,
    city = EXCLUDED.city,
    extracted_category = EXCLUDED.extracted_category,
    year = EXCLUDED.year,
    month = EXCLUDED.month;

-- Verify insert
SELECT
    url,
    title,
    country,
    region,
    city,
    extracted_category,
    year,
    month
FROM scraped_articles
WHERE url = 'https://test.com/migration-007-test';

-- Clean up test data
DELETE FROM scraped_articles WHERE url = 'https://test.com/migration-007-test';

-- Summary
SELECT 'Migration 007 validation completed successfully' AS status;
