# Prochaines Étapes - Système d'Extraction de Métadonnées

## Installation et Déploiement

### Étape 1: Appliquer la Migration SQL

```bash
# Option 1: Via psql
psql -U scraper_user -d scraper_db -f db/migrations/007_add_metadata_columns.sql

# Option 2: Via Docker (si utilisation de conteneur)
docker exec -i postgres_container psql -U scraper_user -d scraper_db < db/migrations/007_add_metadata_columns.sql

# Validation
psql -U scraper_user -d scraper_db -f db/migrations/validate_007.sql
```

**Résultat attendu:**
```
Migration 007 completed successfully: Added metadata columns and indexes
```

### Étape 2: Vérifier l'Installation

```bash
# Lancer les tests unitaires
cd C:/Users/willi/Documents/Projets/VS_CODE/scraper-pro
python -m pytest tests/test_metadata_extractor.py -v

# Résultat attendu: 50+ tests passed
```

### Étape 3: Tester avec le Script de Démonstration

```bash
# Windows
set PYTHONPATH=.
python examples/metadata_extraction_demo.py

# Linux/Mac
export PYTHONPATH=.
python examples/metadata_extraction_demo.py
```

**Résultat attendu:**
- Extraction de métadonnées depuis URLs
- Normalisation des pays
- Statistiques du système

## Premier Scraping avec Métadonnées

### Test sur un Petit Site

```bash
# Scraper 10 articles pour tester
scrapy crawl blog_content \
    -a start_url="https://www.expat.com/en/guide/" \
    -a max_articles=10 \
    -a job_id=TEST_001

# Vérifier les résultats
psql -U scraper_user -d scraper_db
```

```sql
-- Voir les métadonnées extraites
SELECT
    url,
    title,
    country,
    region,
    city,
    extracted_category,
    language,
    year,
    month
FROM scraped_articles
WHERE job_id = 'TEST_001'
ORDER BY scraped_at DESC;

-- Taux de couverture
SELECT
    COUNT(*) as total_articles,
    COUNT(country) as with_country,
    COUNT(region) as with_region,
    COUNT(extracted_category) as with_category,
    ROUND(COUNT(country)::numeric / COUNT(*) * 100, 2) as country_rate,
    ROUND(COUNT(extracted_category)::numeric / COUNT(*) * 100, 2) as category_rate
FROM scraped_articles
WHERE job_id = 'TEST_001';
```

**Taux de couverture attendu:**
- Country: 60-80%
- Region: 60-80%
- Category: 40-60%
- Year: 30-50%

### Scraping Production

Une fois le test validé:

```bash
# Scraping complet
scrapy crawl blog_content \
    -a start_url="https://www.expat.com/en/guide/" \
    -a max_articles=1000 \
    -a scrape_depth=3 \
    -a job_id=PROD_001
```

## Analyse des Résultats

### 1. Vérifier la Distribution Géographique

```sql
-- Top 10 pays
SELECT
    country,
    COUNT(*) as article_count
FROM scraped_articles
WHERE country IS NOT NULL
GROUP BY country
ORDER BY article_count DESC
LIMIT 10;

-- Articles par région
SELECT
    region,
    COUNT(*) as article_count
FROM scraped_articles
WHERE region IS NOT NULL
GROUP BY region
ORDER BY article_count DESC;
```

### 2. Analyser les Catégories

```sql
-- Distribution des catégories
SELECT
    extracted_category,
    COUNT(*) as article_count
FROM scraped_articles
WHERE extracted_category IS NOT NULL
GROUP BY extracted_category
ORDER BY article_count DESC;

-- Catégories par pays
SELECT
    country,
    extracted_category,
    COUNT(*) as article_count
FROM scraped_articles
WHERE country IS NOT NULL
    AND extracted_category IS NOT NULL
GROUP BY country, extracted_category
ORDER BY country, article_count DESC;
```

### 3. Identifier les Gaps de Contenu

```sql
-- Pays/catégories avec peu de contenu (opportunités)
SELECT
    country,
    extracted_category,
    COUNT(*) as article_count
FROM scraped_articles
WHERE country IS NOT NULL
    AND extracted_category IS NOT NULL
GROUP BY country, extracted_category
HAVING COUNT(*) < 5
ORDER BY article_count ASC;
```

### 4. Tendances Temporelles

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

-- Sujets tendance par mois
SELECT
    year,
    month,
    extracted_category,
    COUNT(*) as article_count
FROM scraped_articles
WHERE year = 2024
    AND extracted_category IS NOT NULL
GROUP BY year, month, extracted_category
ORDER BY year DESC, month DESC, article_count DESC;
```

## Personnalisation du Système

### Ajouter de Nouveaux Pays

Éditer `scraper/utils/metadata_extractor.py`:

```python
# Ajouter dans COUNTRY_CODES
COUNTRY_CODES = {
    # ... existing ...
    "nouveau-pays": "nouveau-pays",
    "alias1": "nouveau-pays",
    "alias2": "nouveau-pays",
}

# Ajouter dans COUNTRIES_BY_REGION
COUNTRIES_BY_REGION = {
    "region-appropriee": [
        # ... existing ...
        "nouveau-pays",
    ],
}
```

### Ajouter de Nouvelles Catégories

```python
# Ajouter dans CATEGORY_KEYWORDS
CATEGORY_KEYWORDS = {
    # ... existing ...
    "nouvelle-categorie": [
        "mot-cle1",
        "mot-cle2",
        "keyword1",
        "keyword2",
    ],
}
```

### Ajouter de Nouvelles Villes

Les villes sont détectées via pattern `/city/nom-ville/` dans les URLs.
Pour améliorer la détection:

```python
def _extract_city_from_path(self, path: str) -> Optional[str]:
    """Améliorer la détection de villes."""
    # Pattern existant
    city_pattern = re.compile(r'/(city|ville|ciudad)/([a-z-]+)', re.IGNORECASE)
    match = city_pattern.search(path)
    if match:
        return match.group(2).replace("-", " ").title()

    # Ajouter pattern pour villes majeures
    major_cities = [
        "paris", "london", "tokyo", "bangkok", "barcelona",
        # ... ajouter vos villes ...
    ]
    for city in major_cities:
        if f"/{city}/" in path or f"/{city}-" in path:
            return city.title()

    return None
```

## Optimisations Possibles

### 1. Améliorer le Taux de Couverture

Si le taux de couverture est < 50%:

```python
# Dans le spider, activer la détection depuis le contenu
self.metadata_extractor = MetadataExtractor(enable_content_detection=True)
```

**Impact:** +10-15% de couverture, mais +5-10ms de latence.

### 2. Ajouter des Sources Custom

Créer une méthode custom dans `metadata_extractor.py`:

```python
def extract_from_custom_source(self, response: Any) -> Dict[str, Any]:
    """Extraction depuis une source spécifique à votre site."""
    metadata = {}

    # Exemple: extraire depuis un attribut data-*
    data_country = response.css('[data-country]::attr(data-country)').get()
    if data_country:
        metadata["country"] = COUNTRY_CODES.get(data_country.lower())

    return metadata
```

Puis l'intégrer dans `extract_all()`:

```python
# 6. Extraction custom
custom_meta = self.extract_from_custom_source(response)
for key, value in custom_meta.items():
    if not metadata.get(key):
        metadata[key] = value
        confidence[key] = 0.95
```

### 3. Machine Learning pour Classification

Pour une classification plus précise:

```python
# Installer sklearn
pip install scikit-learn

# Entraîner un modèle sur vos données existantes
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# Charger articles avec catégories connues
# Entraîner le modèle
# Utiliser pour prédire nouvelles catégories
```

## Export et Intégration

### Export CSV des Métadonnées

```sql
-- Export pour analyse externe
COPY (
    SELECT
        url,
        title,
        country,
        region,
        city,
        extracted_category,
        language,
        year,
        month,
        scraped_at
    FROM scraped_articles
    WHERE country IS NOT NULL
    ORDER BY scraped_at DESC
) TO '/tmp/articles_metadata.csv' WITH CSV HEADER;
```

### API REST pour Accès aux Métadonnées

Créer un endpoint Flask/FastAPI:

```python
# api/metadata.py
from flask import Flask, jsonify
from scraper.database import get_db_session
from sqlalchemy import text

app = Flask(__name__)

@app.route('/api/metadata/countries')
def get_countries():
    """Liste des pays avec nombre d'articles."""
    with get_db_session() as session:
        result = session.execute(text("""
            SELECT country, COUNT(*) as count
            FROM scraped_articles
            WHERE country IS NOT NULL
            GROUP BY country
            ORDER BY count DESC
        """))
        return jsonify([dict(r) for r in result])

@app.route('/api/metadata/articles/<country>')
def get_articles_by_country(country):
    """Articles d'un pays spécifique."""
    with get_db_session() as session:
        result = session.execute(text("""
            SELECT url, title, extracted_category, year, month
            FROM scraped_articles
            WHERE country = :country
            ORDER BY scraped_at DESC
            LIMIT 100
        """), {"country": country})
        return jsonify([dict(r) for r in result])
```

### Dashboard Analytique

Utiliser Streamlit pour un dashboard interactif:

```bash
pip install streamlit plotly pandas

# dashboard/metadata_dashboard.py
```

```python
import streamlit as st
import pandas as pd
import plotly.express as px
from scraper.database import get_db_session
from sqlalchemy import text

st.title("📊 Metadata Analytics Dashboard")

# Load data
@st.cache_data
def load_data():
    with get_db_session() as session:
        result = session.execute(text("""
            SELECT country, region, extracted_category, year, month
            FROM scraped_articles
            WHERE country IS NOT NULL
        """))
        return pd.DataFrame(result.fetchall())

df = load_data()

# Widgets
st.sidebar.header("Filters")
selected_region = st.sidebar.multiselect("Region", df["region"].unique())

# Charts
fig = px.bar(
    df["country"].value_counts().head(10),
    title="Top 10 Countries by Articles"
)
st.plotly_chart(fig)
```

Lancer:
```bash
streamlit run dashboard/metadata_dashboard.py
```

## Monitoring et Maintenance

### 1. Surveillance du Taux de Couverture

Créer une alerte si le taux baisse:

```sql
-- Vue pour monitoring
CREATE OR REPLACE VIEW metadata_coverage AS
SELECT
    DATE(scraped_at) as date,
    COUNT(*) as total_articles,
    COUNT(country) as with_country,
    ROUND(COUNT(country)::numeric / COUNT(*) * 100, 2) as coverage_rate
FROM scraped_articles
GROUP BY DATE(scraped_at)
ORDER BY date DESC;

-- Vérifier la couverture aujourd'hui
SELECT * FROM metadata_coverage WHERE date = CURRENT_DATE;
```

### 2. Logs et Debugging

Activer les logs détaillés:

```python
# Dans settings.py de Scrapy
LOG_LEVEL = 'DEBUG'

# Dans metadata_extractor.py
import logging
logger.setLevel(logging.DEBUG)
```

### 3. Performance Monitoring

```sql
-- Temps moyen d'extraction (si logs stockés)
SELECT
    AVG(extraction_time_ms) as avg_extraction_time,
    MAX(extraction_time_ms) as max_extraction_time
FROM scraping_logs
WHERE spider_name = 'blog_content';
```

## Support et Ressources

### Documentation
- **Complète**: `docs/METADATA_EXTRACTION.md`
- **Quick Start**: `docs/QUICK_START_METADATA.md`
- **Changelog**: `CHANGELOG_METADATA.md`
- **Résumé**: `IMPLEMENTATION_SUMMARY.md`

### Code
- **Module**: `scraper/utils/metadata_extractor.py`
- **Tests**: `tests/test_metadata_extractor.py`
- **Démo**: `examples/metadata_extraction_demo.py`

### SQL
- **Migration**: `db/migrations/007_add_metadata_columns.sql`
- **Validation**: `db/migrations/validate_007.sql`

## Checklist Déploiement

- [ ] Migration SQL appliquée et validée
- [ ] Tests unitaires passent (50+)
- [ ] Script de démo fonctionne
- [ ] Test scraping sur 10 articles OK
- [ ] Taux de couverture vérifié (>50%)
- [ ] Requêtes SQL de base testées
- [ ] Documentation lue et comprise
- [ ] Équipe formée sur le système
- [ ] Monitoring mis en place
- [ ] Backup de la base avant production

## Contact et Contribution

Pour améliorer le système:
1. Ajouter des tests pour vos cas d'usage
2. Documenter les patterns spécifiques à vos sites
3. Contribuer de nouveaux pays/villes/catégories
4. Signaler les bugs via issues
5. Proposer des optimisations

---

**Version**: 1.0.0
**Statut**: Production Ready
**Date**: 2026-02-13

**Bonne chance avec votre scraping!** 🚀
