# Quick Start - Système d'Extraction de Métadonnées

## Installation en 3 étapes

### 1. Appliquer la Migration Base de Données

```bash
# Connexion à PostgreSQL
psql -U scraper_user -d scraper_db

# Exécuter la migration
\i db/migrations/007_add_metadata_columns.sql

# Valider la migration
\i db/migrations/validate_007.sql

# Quitter
\q
```

### 2. Vérifier l'Installation

```bash
# Lancer les tests
python -m pytest tests/test_metadata_extractor.py -v

# Tous les tests doivent passer (12/12)
```

### 3. Tester avec le Script Demo

```bash
# Exécuter le script de démonstration
python examples/metadata_extraction_demo.py
```

## Utilisation Immédiate

### Dans le Spider (Automatique)

Le système fonctionne automatiquement dès que vous lancez le spider:

```bash
# Scraper un blog - les métadonnées sont extraites automatiquement
scrapy crawl blog_content \
    -a start_url="https://www.expat.com/en/guide/" \
    -a max_articles=50 \
    -a job_id=123
```

### Vérifier les Résultats

```sql
-- Voir les métadonnées extraites
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
WHERE job_id = 123
ORDER BY scraped_at DESC
LIMIT 10;
```

## Exemples de Requêtes SQL

### 1. Articles par Pays

```sql
SELECT
    country,
    COUNT(*) as total_articles
FROM scraped_articles
WHERE country IS NOT NULL
GROUP BY country
ORDER BY total_articles DESC
LIMIT 10;
```

### 2. Articles par Catégorie

```sql
SELECT
    extracted_category,
    COUNT(*) as total_articles
FROM scraped_articles
WHERE extracted_category IS NOT NULL
GROUP BY extracted_category
ORDER BY total_articles DESC;
```

### 3. Articles Récents sur une Destination

```sql
SELECT
    title,
    url,
    city,
    extracted_category,
    year,
    month
FROM scraped_articles
WHERE country = 'france'
    AND city = 'paris'
    AND year = 2024
ORDER BY month DESC;
```

### 4. Gaps de Contenu (Opportunités)

```sql
-- Trouver les pays/catégories avec peu de contenu
SELECT
    country,
    extracted_category,
    COUNT(*) as article_count
FROM scraped_articles
WHERE country IS NOT NULL
    AND extracted_category IS NOT NULL
GROUP BY country, extracted_category
HAVING COUNT(*) < 5
ORDER BY country, extracted_category;
```

### 5. Tendances Temporelles

```sql
-- Évolution mensuelle des publications
SELECT
    year,
    month,
    COUNT(*) as total_articles
FROM scraped_articles
WHERE year >= 2023
GROUP BY year, month
ORDER BY year DESC, month DESC;
```

## Métadonnées Disponibles

| Champ | Type | Description | Exemple |
|-------|------|-------------|---------|
| `country` | VARCHAR(100) | Pays normalisé | "france", "spain" |
| `region` | VARCHAR(50) | Région géographique | "europe", "asia" |
| `city` | VARCHAR(100) | Ville détectée | "paris", "bangkok" |
| `extracted_category` | VARCHAR(100) | Catégorie automatique | "visa", "housing" |
| `extracted_subcategory` | VARCHAR(100) | Sous-catégorie | (future) |
| `year` | INTEGER | Année de publication | 2024 |
| `month` | INTEGER | Mois (1-12) | 3 |

## Sources d'Extraction

Le système extrait les métadonnées depuis (par ordre de priorité):

1. **URL** (confiance: 90%)
   - `/france/paris/visa-guide/`
   - `/2024/01/article/`

2. **Breadcrumbs** (confiance: 80%)
   - `Home > Voyages > Europe > France`

3. **Schema.org JSON-LD** (confiance: 85%)
   - `"inLanguage": "fr-FR"`
   - `"contentLocation": {"name": "Paris, France"}`

4. **Meta Tags** (confiance: 70%)
   - `<meta property="og:locale" content="fr_FR">`
   - `<meta name="geo.placename" content="Paris">`

5. **Contenu** (confiance: 50%)
   - Détection automatique de langue
   - Mentions de pays dans le texte

## Pays et Régions Supportés

### Europe (29 pays)
france, germany, spain, italy, united-kingdom, netherlands, belgium, switzerland, austria, sweden, norway, denmark, finland, poland, czech-republic, hungary, romania, greece, ireland, portugal, etc.

### Asie (15 pays)
china, japan, south-korea, india, thailand, vietnam, indonesia, malaysia, singapore, philippines, pakistan, bangladesh, etc.

### Amérique (11 pays)
usa, canada, mexico, brazil, argentina, chile, colombia, peru, venezuela, ecuador, uruguay

### Autres Régions
africa (7 pays), middle-east (4 pays), oceania (2 pays)

**Total: 70+ pays reconnus**

## Catégories Supportées

1. **guide** - Guides, tutoriels, conseils
2. **news** - Actualités, nouvelles
3. **lifestyle** - Style de vie
4. **travel** - Voyage, tourisme
5. **work** - Travail, emploi
6. **housing** - Logement
7. **health** - Santé
8. **finance** - Finance, banque
9. **education** - Éducation
10. **culture** - Culture, art
11. **food** - Gastronomie
12. **tech** - Technologie
13. **business** - Business
14. **legal** - Juridique, visa
15. **sports** - Sport
16. **entertainment** - Divertissement

## Dépannage

### Métadonnées Non Extraites

**Problème**: Certains articles n'ont pas de métadonnées.

**Solutions**:
1. Vérifier que l'URL contient des indices:
   ```sql
   SELECT url FROM scraped_articles WHERE country IS NULL LIMIT 10;
   ```

2. Analyser manuellement une URL:
   ```python
   from scraper.utils.metadata_extractor import MetadataExtractor

   extractor = MetadataExtractor()
   metadata = extractor.extract_from_url("https://example.com/path/")
   print(metadata)
   ```

### Taux de Couverture Faible

**Problème**: Moins de 50% des articles ont des métadonnées.

**Solutions**:
1. Vérifier le taux de couverture:
   ```sql
   SELECT
       COUNT(*) as total,
       COUNT(country) as with_country,
       ROUND(COUNT(country)::numeric / COUNT(*) * 100, 2) as rate
   FROM scraped_articles;
   ```

2. Ajouter de nouveaux patterns dans `metadata_extractor.py`

3. Activer la détection depuis le contenu:
   ```python
   extractor = MetadataExtractor(enable_content_detection=True)
   ```

## Performance

### Impact Minimal

- **Overhead**: 5-10ms par article
- **Aucune requête réseau** supplémentaire
- **Traitement 100% local**
- **Optimisé** avec regex compilées

### Monitoring

```sql
-- Performance de l'extraction (taux de succès)
SELECT
    COUNT(*) as total_articles,
    COUNT(country) as with_country,
    COUNT(region) as with_region,
    COUNT(extracted_category) as with_category,
    COUNT(year) as with_year,
    ROUND(AVG(
        CASE WHEN country IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN region IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN extracted_category IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END
    ) / 4.0 * 100, 2) as avg_coverage_rate
FROM scraped_articles;
```

## Prochaines Étapes

1. **Explorer la documentation complète**
   ```bash
   cat docs/METADATA_EXTRACTION.md
   ```

2. **Lancer un scraping de test**
   ```bash
   scrapy crawl blog_content -a start_url="https://example.com/blog"
   ```

3. **Analyser les résultats**
   ```sql
   SELECT * FROM scraped_articles ORDER BY scraped_at DESC LIMIT 20;
   ```

4. **Personnaliser l'extracteur**
   - Ajouter vos propres pays/villes
   - Définir vos catégories custom
   - Ajuster les patterns regex

## Support

- **Documentation**: `docs/METADATA_EXTRACTION.md`
- **Tests**: `tests/test_metadata_extractor.py`
- **Exemples**: `examples/metadata_extraction_demo.py`
- **Changelog**: `CHANGELOG_METADATA.md`

---

**Version**: 1.0.0
**Date**: 2026-02-13
**Status**: Production Ready
