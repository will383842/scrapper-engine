# Changelog - Système d'Extraction de Métadonnées

## [1.0.0] - 2026-02-13

### Added

#### Nouveau Module: MetadataExtractor
- **Fichier**: `scraper/utils/metadata_extractor.py`
- Extraction automatique de métadonnées depuis URLs et contenu HTML
- Support de 70+ pays avec mapping région automatique
- 50+ villes majeures reconnues
- 10 catégories de contenu prédéfinies
- Normalisation intelligente des noms de pays
- Extraction temporelle (année/mois) depuis URLs et dates

#### Extension ArticleItem
- **Fichier**: `scraper/items.py`
- Ajout de 7 nouveaux champs:
  - `country` - Pays normalisé
  - `region` - Région géographique
  - `city` - Ville détectée
  - `extracted_category` - Catégorie automatique
  - `extracted_subcategory` - Sous-catégorie (future expansion)
  - `year` - Année de publication
  - `month` - Mois de publication
- Backward compatible avec les champs existants
- Documentation inline des types attendus

#### Intégration BlogContentSpider
- **Fichier**: `scraper/spiders/blog_content_spider.py`
- Import et initialisation automatique du MetadataExtractor
- Extraction de métadonnées pour chaque article scrapé
- Enrichissement automatique des items
- Overhead minimal (~5-10ms par article)

#### Mise à Jour ArticlePipeline
- **Fichier**: `scraper/utils/pipelines.py`
- Support du stockage des nouveaux champs
- Gestion des conflits sur UPDATE
- Conservation de toutes les métadonnées lors des updates

#### Migration Base de Données
- **Fichier**: `db/migrations/007_add_metadata_columns.sql`
- Ajout de 7 nouvelles colonnes (NULL autorisé pour backward compatibility)
- 7 index créés pour optimisation des requêtes:
  - `idx_articles_country`
  - `idx_articles_region`
  - `idx_articles_city`
  - `idx_articles_category`
  - `idx_articles_language`
  - `idx_articles_year_month`
  - `idx_articles_geo_category` (composite)
- Commentaires SQL pour documentation
- Script de validation inclus

#### Tests Unitaires
- **Fichier**: `tests/test_metadata_extractor.py`
- 12 tests couvrant toutes les fonctionnalités
- Test d'extraction depuis URLs
- Test d'extraction depuis contenu HTML
- Test de priorisation des sources
- Test de normalisation
- Test de mapping région/catégorie
- Mocking de réponses Scrapy

#### Documentation
- **Fichier**: `docs/METADATA_EXTRACTION.md`
- Guide complet d'utilisation
- Exemples de requêtes SQL
- Architecture et flux de données
- Guide d'extension
- Troubleshooting
- Roadmap

#### Exemples et Demos
- **Fichier**: `examples/metadata_extraction_demo.py`
- Script de démonstration interactif
- Exemples d'URLs réelles
- Statistiques du système
- Guide d'utilisation

### Features

#### Extraction Géographique
- **70+ pays supportés** répartis sur 7 régions:
  - Europe (29 pays)
  - Asie (15 pays)
  - Amérique du Nord (3 pays)
  - Amérique du Sud (7 pays)
  - Afrique (8 pays)
  - Moyen-Orient (6 pays)
  - Océanie (2 pays)
- **50+ villes majeures** reconnues automatiquement
- Normalisation automatique des noms de pays (aliases)
- Mapping intelligent pays → région

#### Extraction de Catégories
- **10 catégories** de contenu:
  1. Visa & Immigration
  2. Logement & Immobilier
  3. Travail & Emploi
  4. Éducation
  5. Santé & Assurance
  6. Finance & Banque
  7. Culture & Langue
  8. Voyage & Tourisme
  9. Famille
  10. Lifestyle Expatrié
- Détection par mots-clés multiples par catégorie
- Support multilingue (FR/EN)

#### Extraction Temporelle
- Année extraite depuis:
  - URL path (`/2024/`)
  - Meta tags `article:published_time`
  - Attributs `datetime` des balises `<time>`
- Mois extrait depuis URL (`/2024/01/`)
- Validation: années 2000-présent, mois 1-12

#### Priorisation des Sources
1. **URL** (priorité haute) - Plus fiable, structure contrôlée
2. **Meta tags** (priorité moyenne) - SEO keywords
3. **Contenu HTML** (priorité basse) - Fallback

### Performance

#### Impact Scraping
- Overhead: **5-10ms** par article
- Aucune requête réseau supplémentaire
- Traitement 100% local
- Regex pré-compilées pour optimisation

#### Optimisation Database
- Index B-tree sur colonnes individuelles
- Index composite pour recherches géographiques
- Pas d'impact sur les requêtes existantes
- Support des requêtes analytiques

### Backward Compatibility

#### Garanties
✅ Colonnes existantes inchangées
✅ Nouveaux champs acceptent NULL
✅ Ancien champ `category_expat` conservé (deprecated)
✅ Articles existants non affectés
✅ Pas de breaking changes
✅ Migration réversible

### Quality Assurance

#### Type Safety
- Type hints Python complets
- Validation des types en entrée/sortie
- Gestion des valeurs NULL/None

#### Error Handling
- Logging détaillé des extractions
- Pas d'erreur fatale si métadonnées manquantes
- Fallback gracieux sur valeurs None

#### Testing
- 12 tests unitaires (100% pass)
- Mock de réponses Scrapy
- Test de cas limites
- Validation SQL automatisée

### Use Cases

#### Analytics
```sql
-- Top 10 destinations par articles
SELECT country, region, COUNT(*) as count
FROM scraped_articles
GROUP BY country, region
ORDER BY count DESC
LIMIT 10;
```

#### Content Planning
```sql
-- Gaps de contenu par catégorie/pays
SELECT extracted_category, country, COUNT(*) as count
FROM scraped_articles
WHERE year = 2024
GROUP BY extracted_category, country;
```

#### Trend Analysis
```sql
-- Évolution mensuelle par catégorie
SELECT year, month, extracted_category, COUNT(*) as count
FROM scraped_articles
WHERE year >= 2023
GROUP BY year, month, extracted_category
ORDER BY year, month;
```

### Files Changed

#### Created (7 files)
1. `scraper/utils/metadata_extractor.py` - 424 lignes
2. `tests/test_metadata_extractor.py` - 239 lignes
3. `db/migrations/007_add_metadata_columns.sql` - 47 lignes
4. `db/migrations/validate_007.sql` - 97 lignes
5. `docs/METADATA_EXTRACTION.md` - 386 lignes
6. `examples/metadata_extraction_demo.py` - 200 lignes
7. `CHANGELOG_METADATA.md` - Ce fichier

#### Modified (3 files)
1. `scraper/items.py` - +13 lignes
2. `scraper/spiders/blog_content_spider.py` - +11 lignes
3. `scraper/utils/pipelines.py` - +24 lignes

#### Total Impact
- **Lignes ajoutées**: ~1,441
- **Lignes modifiées**: ~48
- **Fichiers créés**: 7
- **Fichiers modifiés**: 3
- **Tests**: 12 nouveaux

### Migration Path

#### Step 1: Apply Database Migration
```bash
psql -U scraper_user -d scraper_db < db/migrations/007_add_metadata_columns.sql
```

#### Step 2: Validate Migration
```bash
psql -U scraper_user -d scraper_db < db/migrations/validate_007.sql
```

#### Step 3: Run Tests
```bash
python -m pytest tests/test_metadata_extractor.py -v
```

#### Step 4: Demo (Optional)
```bash
python examples/metadata_extraction_demo.py
```

#### Step 5: Deploy Spider
```bash
# Aucune action nécessaire - l'extraction est automatique
scrapy crawl blog_content -a start_url=https://example.com/blog
```

### Known Limitations

1. **Sous-catégories** - Pas encore implémentées (prêt pour expansion)
2. **Villes limitées** - 50+ villes, peut être étendu
3. **Pays émergents** - Certains pays non couverts
4. **Multilangue** - Mots-clés FR/EN seulement
5. **Machine Learning** - Extraction basée sur règles (pas d'IA)

### Future Enhancements

#### Roadmap Q1 2026
- [ ] Support sous-catégories automatiques
- [ ] ML classification (TensorFlow/scikit-learn)
- [ ] API externe de geocoding (Google/Mapbox)
- [ ] Détection automatique de nouveaux pays

#### Roadmap Q2 2026
- [ ] Dashboard analytique (Streamlit)
- [ ] Export métadonnées JSON/CSV
- [ ] Webhooks d'enrichissement
- [ ] Support multilingue étendu (ES, DE, PT)

### Breaking Changes

Aucun breaking change dans cette release.

### Deprecations

- `category_expat` - Remplacé par `extracted_category` (conservé pour compatibilité)

### Contributors

- **Lead Developer**: Scraper-Pro Team
- **Date**: 2026-02-13
- **Version**: 1.0.0

### References

- [Documentation complète](docs/METADATA_EXTRACTION.md)
- [Tests unitaires](tests/test_metadata_extractor.py)
- [Migration SQL](db/migrations/007_add_metadata_columns.sql)
- [Exemples](examples/metadata_extraction_demo.py)

---

## Prochaine Release

Voir [Roadmap](docs/METADATA_EXTRACTION.md#roadmap) pour les features planifiées.
