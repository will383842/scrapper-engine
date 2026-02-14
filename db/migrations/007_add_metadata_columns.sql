-- Migration 007: Add universal metadata columns to scraped_articles
-- Date: 2026-02-13
-- Description: Support extraction automatique de métadonnées géographiques, temporelles et de classification

-- Ajouter colonnes géographiques
ALTER TABLE scraped_articles ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE scraped_articles ADD COLUMN IF NOT EXISTS region VARCHAR(50);
ALTER TABLE scraped_articles ADD COLUMN IF NOT EXISTS city VARCHAR(100);

-- Ajouter colonnes classification
ALTER TABLE scraped_articles ADD COLUMN IF NOT EXISTS extracted_category VARCHAR(100);
ALTER TABLE scraped_articles ADD COLUMN IF NOT EXISTS extracted_subcategory VARCHAR(100);

-- Ajouter colonnes temporelles
ALTER TABLE scraped_articles ADD COLUMN IF NOT EXISTS year INTEGER;
ALTER TABLE scraped_articles ADD COLUMN IF NOT EXISTS month INTEGER;

-- Créer index pour recherche rapide
CREATE INDEX IF NOT EXISTS idx_articles_country ON scraped_articles(country);
CREATE INDEX IF NOT EXISTS idx_articles_region ON scraped_articles(region);
CREATE INDEX IF NOT EXISTS idx_articles_city ON scraped_articles(city);
CREATE INDEX IF NOT EXISTS idx_articles_category ON scraped_articles(extracted_category);
CREATE INDEX IF NOT EXISTS idx_articles_language ON scraped_articles(language);
CREATE INDEX IF NOT EXISTS idx_articles_year_month ON scraped_articles(year, month);

-- Créer index composite pour recherches géographiques complexes
CREATE INDEX IF NOT EXISTS idx_articles_geo_category ON scraped_articles(country, region, extracted_category);

-- Commentaires pour documentation
COMMENT ON COLUMN scraped_articles.country IS 'Pays extrait automatiquement (code ou nom normalisé)';
COMMENT ON COLUMN scraped_articles.region IS 'Région géographique (europe, asia, africa, north-america, south-america, middle-east, oceania)';
COMMENT ON COLUMN scraped_articles.city IS 'Ville extraite depuis URL ou contenu';
COMMENT ON COLUMN scraped_articles.extracted_category IS 'Catégorie extraite automatiquement (visa, housing, work, education, etc.)';
COMMENT ON COLUMN scraped_articles.extracted_subcategory IS 'Sous-catégorie extraite';
COMMENT ON COLUMN scraped_articles.year IS 'Année de publication extraite (YYYY)';
COMMENT ON COLUMN scraped_articles.month IS 'Mois de publication extrait (1-12)';

-- Migration réussie
SELECT 'Migration 007 completed successfully: Added metadata columns and indexes' AS status;
