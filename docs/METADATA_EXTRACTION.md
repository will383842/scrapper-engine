# Système d'Extraction de Métadonnées Universelles

## Vue d'ensemble

Le système d'extraction de métadonnées permet de collecter automatiquement des informations géographiques, temporelles et de classification à partir des URLs et du contenu des articles scrapés.

## Architecture

### Composants

1. **MetadataExtractor** (`scraper/utils/metadata_extractor.py`)
   - Classe principale d'extraction de métadonnées
   - Analyse les URLs et le contenu HTML
   - Normalisation des données géographiques

2. **ArticleItem** (`scraper/items.py`)
   - Champs de métadonnées ajoutés
   - Compatible avec les anciens champs

3. **BlogContentSpider** (`scraper/spiders/blog_content_spider.py`)
   - Intégration du MetadataExtractor
   - Extraction automatique lors du scraping

4. **ArticlePipeline** (`scraper/utils/pipelines.py`)
   - Stockage des métadonnées en base de données
   - Gestion des conflits

## Métadonnées Extraites

### Géographiques

- **country** (VARCHAR 100): Pays normalisé (ex: "france", "spain", "usa")
- **region** (VARCHAR 50): Région géographique
  - `europe`
  - `asia`
  - `north-america`
  - `south-america`
  - `africa`
  - `middle-east`
  - `oceania`
- **city** (VARCHAR 100): Ville extraite (ex: "paris", "bangkok")

### Classification

- **extracted_category** (VARCHAR 100): Catégorie automatique
  - `visa` - Immigration, permis, résidence
  - `housing` - Logement, immobilier
  - `work` - Emploi, carrière, salaire
  - `education` - Écoles, universités
  - `healthcare` - Santé, assurance
  - `finance` - Banque, impôts, budget
  - `culture` - Culture, langue, traditions
  - `travel` - Voyage, tourisme
  - `family` - Famille, enfants
  - `lifestyle` - Vie d'expatrié

- **extracted_subcategory** (VARCHAR 100): Sous-catégorie (future expansion)

### Temporelles

- **year** (INTEGER): Année de publication (2000-présent)
- **month** (INTEGER): Mois de publication (1-12)

## Sources d'Extraction

### 1. URL (Priorité Haute)

```python
# Exemples d'extraction depuis URL
"/expat/france/paris/visa-2024/"
  → country: "france"
  → region: "europe"
  → city: "paris"
  → category: "visa"
  → year: 2024

"/blog/2024/01/living-in-bangkok/"
  → city: "bangkok"
  → year: 2024
  → month: 1
```

### 2. Meta Tags (Priorité Moyenne)

```html
<meta name="keywords" content="france, paris, visa, immigration">
<!-- Extrait: country="france", city="paris", category="visa" -->
```

### 3. Contenu HTML (Priorité Basse)

```html
<title>Living in Paris: Complete Guide</title>
<!-- Extrait: city="paris" -->

<div class="category">
  <a href="/category/visa">Visa</a>
</div>
<!-- Extrait: category="visa" -->

<time datetime="2024-03-15T10:00:00Z">
<!-- Extrait: year=2024, month=3 -->
```

## Migration Base de Données

### Exécution

```bash
# Se connecter à PostgreSQL
psql -U scraper_user -d scraper_db

# Exécuter la migration
\i db/migrations/007_add_metadata_columns.sql
```

### Index Créés

```sql
-- Index simples
idx_articles_country
idx_articles_region
idx_articles_city
idx_articles_category
idx_articles_language
idx_articles_year_month

-- Index composite pour recherches complexes
idx_articles_geo_category (country, region, extracted_category)
```

## Utilisation

### Dans le Spider

Le système est automatiquement activé dans `BlogContentSpider`:

```python
# L'extraction se fait automatiquement
metadata = self.metadata_extractor.extract_all(response.url, response)

# Les métadonnées sont ajoutées à l'item
item = ArticleItem(
    # ... champs standard ...
    country=metadata.get("country"),
    region=metadata.get("region"),
    city=metadata.get("city"),
    extracted_category=metadata.get("category"),
    year=metadata.get("year"),
    month=metadata.get("month"),
)
```

### Requêtes SQL

```sql
-- Articles sur la France
SELECT * FROM scraped_articles WHERE country = 'france';

-- Articles sur les visas en Europe
SELECT * FROM scraped_articles
WHERE region = 'europe' AND extracted_category = 'visa';

-- Articles récents sur Paris
SELECT * FROM scraped_articles
WHERE city = 'paris' AND year = 2024;

-- Top des catégories par région
SELECT region, extracted_category, COUNT(*) as count
FROM scraped_articles
WHERE region IS NOT NULL
GROUP BY region, extracted_category
ORDER BY region, count DESC;
```

## Tests

### Exécution des Tests

```bash
# Installer pytest si nécessaire
pip install pytest

# Exécuter les tests
python -m pytest tests/test_metadata_extractor.py -v

# Avec couverture
python -m pytest tests/test_metadata_extractor.py --cov=scraper.utils.metadata_extractor
```

### Couverture

Les tests couvrent:
- ✓ Extraction depuis URL
- ✓ Extraction depuis contenu HTML
- ✓ Priorité des sources (URL > Meta > Contenu)
- ✓ Normalisation des pays
- ✓ Mapping pays → région
- ✓ Validation année/mois
- ✓ Mapping mots-clés → catégories

## Extension du Système

### Ajouter un Nouveau Pays

```python
# Dans MetadataExtractor.COUNTRY_TO_REGION
COUNTRY_TO_REGION = {
    # ...
    "nouveau-pays": "region",
}
```

### Ajouter une Nouvelle Ville

```python
# Dans MetadataExtractor.CITY_PATTERNS
CITY_PATTERNS = [
    # ...
    "nouvelle-ville",
]
```

### Ajouter une Nouvelle Catégorie

```python
# Dans MetadataExtractor.CATEGORY_KEYWORDS
CATEGORY_KEYWORDS = {
    # ...
    "nouvelle-categorie": ["mot-cle1", "mot-cle2"],
}
```

## Backward Compatibility

Le système est entièrement rétrocompatible:

- Les anciennes colonnes restent inchangées
- Les nouveaux champs acceptent NULL
- Le champ `category_expat` est conservé (deprecated)
- Les articles existants ne sont pas affectés

## Performance

### Impact sur le Scraping

- Overhead: ~5-10ms par article
- Pas de requêtes réseau supplémentaires
- Traitement entièrement local
- Optimisé avec regex compilées

### Optimisations Database

- Index sur les colonnes fréquemment requêtées
- Index composite pour les recherches multi-critères
- Pas de perte de performance sur les requêtes existantes

## Monitoring

### Vérifier l'Extraction

```sql
-- Taux de couverture par métadonnée
SELECT
    COUNT(*) as total,
    COUNT(country) as with_country,
    COUNT(region) as with_region,
    COUNT(city) as with_city,
    COUNT(extracted_category) as with_category,
    COUNT(year) as with_year,
    ROUND(COUNT(country)::numeric / COUNT(*) * 100, 2) as country_rate
FROM scraped_articles;
```

### Qualité des Données

```sql
-- Distribution des pays
SELECT country, COUNT(*) as count
FROM scraped_articles
WHERE country IS NOT NULL
GROUP BY country
ORDER BY count DESC
LIMIT 20;

-- Distribution des catégories
SELECT extracted_category, COUNT(*) as count
FROM scraped_articles
WHERE extracted_category IS NOT NULL
GROUP BY extracted_category
ORDER BY count DESC;
```

## Troubleshooting

### Métadonnées Non Extraites

1. Vérifier que l'URL contient des indices géographiques
2. Vérifier les meta tags du site
3. Ajouter de nouveaux patterns si nécessaire
4. Consulter les logs du spider

### Valeurs Incorrectes

1. Vérifier la normalisation dans `normalize_country()`
2. Ajouter des alias si nécessaire
3. Affiner les regex de détection
4. Utiliser les catégories du site (fallback)

## Roadmap

- [ ] Support sous-catégories
- [ ] Machine Learning pour classification
- [ ] Détection automatique de nouveaux pays/villes
- [ ] API d'enrichissement externe (Geocoding)
- [ ] Dashboard analytique
- [ ] Export métadonnées en JSON/CSV

## Auteur

Scraper-Pro Team - 2026-02-13
