# Extracteur Universel de Métadonnées

**Version:** 1.0.0
**Auteur:** Scraper-Pro
**Fichier:** `scraper/utils/metadata_extractor.py`

## Vue d'ensemble

Classe Python ultra-intelligente qui extrait automatiquement **langue, pays, catégorie, région, ville et dates** depuis n'importe quel site web.

Fonctionne en analysant **5 sources** dans l'ordre de priorité suivant:

1. **URL** (haute confiance: 0.9)
2. **Breadcrumbs** (fil d'Ariane) (confiance: 0.8)
3. **Schema.org JSON-LD** (confiance: 0.85)
4. **Meta tags** (confiance: 0.7)
5. **Contenu texte** (fallback, confiance: 0.5)

## Installation

```bash
pip install langdetect
```

Ou ajoutez à `requirements.txt`:

```
langdetect==1.0.*
```

## Usage Basique

```python
from scraper.utils.metadata_extractor import MetadataExtractor

# Initialiser l'extracteur
extractor = MetadataExtractor()

# Extraire métadonnées depuis Scrapy Response
metadata = extractor.extract_all(url, response)

# Résultat
{
    "language": "fr",
    "country": "france",
    "region": "europe",
    "category": "housing",
    "city": "paris",
    "year": 2024,
    "month": 1,
    "confidence": {
        "language": 0.9,
        "country": 0.9,
        "category": 0.8
    }
}
```

## Avec détection de langue depuis contenu

```python
extractor = MetadataExtractor(enable_content_detection=True)

metadata = extractor.extract_all(
    url="https://blog.com/article",
    response=response,
    content_text="Texte de l'article..."
)
```

## Fonctionnalités

### 1. Extraction depuis URL

Détecte automatiquement:

- **Langue:** `/fr/`, `/en-us/`, `/de/`
- **Pays:** `/france/`, `/spain/`, `/thailand/`
- **Catégorie:** `/category/travel/`, `/categorie/logement/`
- **Date:** `/2024/01/`, `/2024-01-15/`
- **Région:** `/europe/`, `/asia/`

**Exemple:**

```python
url = "https://blog.com/fr/europe/spain/category/travel/2024/01/article"

# Extrait:
# - language: fr
# - region: europe
# - country: spain
# - category: travel
# - year: 2024, month: 1
```

### 2. Extraction depuis Breadcrumbs

Analyse le fil d'Ariane:

```html
<nav class="breadcrumb">
  <a>Home</a> > <a>Travel</a> > <a>Europe</a> > <a>France</a>
</nav>
```

Extrait: `category=travel`, `region=europe`, `country=france`

Sélecteurs CSS supportés:
- `.breadcrumb a::text`
- `.breadcrumbs a::text`
- `[itemtype*="BreadcrumbList"] a::text`
- `nav ol li a::text`
- `.trail-items a::text`

### 3. Extraction depuis Schema.org

Parse JSON-LD:

```html
<script type="application/ld+json">
{
  "@type": "Article",
  "articleSection": "Technology",
  "inLanguage": "fr-FR",
  "contentLocation": {"name": "Paris, France"},
  "keywords": "tech, ai, europe"
}
</script>
```

Extrait:
- `category=tech` (depuis articleSection)
- `language=fr` (depuis inLanguage)
- `country=france`, `city=Paris` (depuis contentLocation)

### 4. Extraction depuis Meta Tags

Analyse balises meta:

```html
<meta property="article:section" content="Business" />
<meta property="og:locale" content="fr_FR" />
<meta name="geo.region" content="FR-75" />
<meta name="geo.placename" content="Paris" />
<meta property="article:tag" content="Travel,Europe,France" />
```

### 5. Extraction depuis Contenu

Détection de langue via `langdetect` + recherche de pays:

```python
text = """
Living in Thailand is an amazing experience. Bangkok offers
a great quality of life and the people are very friendly.
"""

# Extrait: country=thailand, language=en (auto-détecté)
```

## Dictionnaires de Mapping

### Langues supportées (30+)

Français, Anglais, Espagnol, Allemand, Portugais, Italien, Néerlandais, Russe, Chinois, Japonais, Coréen, Arabe, Hindi, Polonais, Turc, Suédois, Norvégien, Danois, Finnois, Tchèque, Hongrois, Roumain, Grec, Hébreu, Thaï, Vietnamien, Indonésien, Malais...

### Pays supportés (60+)

Europe, Asie, Afrique, Amériques, Océanie, Moyen-Orient.

Avec alias:
- `united-states` → `usa`
- `united-kingdom` → `uk`
- `deutschland` → `germany`

### Catégories (16)

`guide`, `news`, `lifestyle`, `travel`, `work`, `housing`, `health`, `finance`, `education`, `culture`, `food`, `tech`, `business`, `legal`, `sports`, `entertainment`

### Régions (8)

`europe`, `asia`, `africa`, `americas`, `north-america`, `south-america`, `oceania`, `middle-east`

## Normalisation Automatique

```python
raw = {
    "language": "FR-FR",
    "country": "FRANCE",
    "category": "TRAVEL"
}

normalized = extractor.normalize_metadata(raw)
# {
#     "language": "fr",
#     "country": "france",
#     "category": "travel"
# }
```

## Inférence de Région

Si pays détecté mais pas région:

```python
metadata["country"] = "germany"
# → Inférence automatique: metadata["region"] = "europe"
```

## Scores de Confiance

Chaque métadonnée extraite a un score de confiance:

- **URL:** 0.9 (très fiable)
- **Schema.org:** 0.85
- **Breadcrumbs:** 0.8
- **Meta tags:** 0.7
- **Contenu:** 0.5 (moins fiable)

```python
metadata["confidence"] = {
    "language": 0.9,  # Depuis URL
    "country": 0.8,   # Depuis breadcrumbs
    "category": 0.7   # Depuis meta tags
}
```

## Intégration avec Scrapy Spider

```python
from scraper.utils.metadata_extractor import MetadataExtractor
from scraper.items import ArticleItem

class BlogSpider(scrapy.Spider):
    name = "blog_spider"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata_extractor = MetadataExtractor()

    def parse_article(self, response):
        # Extraire article
        article_data = self._extract_article(response)

        # Extraire métadonnées
        metadata = self.metadata_extractor.extract_all(
            url=response.url,
            response=response,
            content_text=article_data.get("content_text")
        )

        # Yield item
        yield ArticleItem(
            title=article_data["title"],
            content_text=article_data["content_text"],
            language=metadata.get("language"),
            country=metadata.get("country"),
            region=metadata.get("region"),
            category=metadata.get("category"),
            city=metadata.get("city"),
            year=metadata.get("year"),
            month=metadata.get("month"),
            source_url=response.url
        )
```

## Cas d'Usage

### Blog Expat

```python
url = "https://expatblog.com/fr/europe/spain/category/housing/2024/01/barcelona"

metadata = extractor.extract_all(url, response)
# {
#   "language": "fr",
#   "region": "europe",
#   "country": "spain",
#   "category": "housing",
#   "year": 2024,
#   "month": 1
# }
```

### Blog Tech

```python
url = "https://techblog.com/en-us/category/technology/2024/02/ai-trends"

metadata = extractor.extract_all(url, response)
# {
#   "language": "en",
#   "country": "usa",
#   "category": "tech",
#   "year": 2024,
#   "month": 2
# }
```

### Site Expat.com

```python
url = "https://www.expat.com/en/guide/europe/france/paris/living-in-paris.html"

metadata = extractor.extract_all(url, response)
# {
#   "language": "en",
#   "region": "europe",
#   "country": "france"
# }
```

## Tests

32 tests unitaires couvrent:

- Extraction depuis URLs (7 tests)
- Extraction depuis breadcrumbs (3 tests)
- Extraction depuis Schema.org (4 tests)
- Extraction depuis meta tags (4 tests)
- Extraction depuis contenu (3 tests)
- Pipeline complet (4 tests)
- Normalisation (3 tests)
- Cas limites (4 tests)

```bash
# Lancer tous les tests
pytest tests/test_metadata_extractor.py -v

# Résultat
# 32 passed in 0.24s
```

## Performance

- **Regex pré-compilés** pour pattern matching rapide
- **Import lazy** de `langdetect` (chargé uniquement si nécessaire)
- **Cache intelligent** pour éviter recherches répétées
- Traite **~100 URLs/seconde** sur hardware standard

## Gestion des Erreurs

```python
try:
    metadata = extractor.extract_all(url, response)
except Exception as e:
    logger.error(f"Metadata extraction failed: {e}")
    metadata = {}  # Fallback safe
```

L'extracteur est **fail-safe**: même en cas d'erreur, retourne un dict vide plutôt que de crasher.

## Extensions Futures

- [ ] Support villes (200+ villes mondiales)
- [ ] Détection sous-catégories (ex: housing → apartment, house)
- [ ] Support multilingue avancé (translittération)
- [ ] API REST pour extraction via HTTP
- [ ] Cache Redis pour métadonnées fréquentes

## License

Propriétaire - Scraper-Pro © 2024

## Support

Pour bugs ou demandes de features, contacter l'équipe dev Scraper-Pro.
