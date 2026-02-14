"""
Extracteur Universel de Métadonnées pour Articles de Blog.

Ce module fournit une classe intelligente qui extrait automatiquement
langue, pays, catégorie et région depuis n'importe quel site web via:
- Pattern matching dans les URLs
- Extraction depuis breadcrumbs (fil d'Ariane)
- Parsing de Schema.org JSON-LD
- Lecture des meta tags
- Détection depuis le contenu (fallback)

Author: Scraper-Pro
Version: 1.0.0
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ============================================================================
# DICTIONNAIRES DE MAPPING
# ============================================================================

LANGUAGE_CODES = {
    # Français
    "fr": "fr", "fr-fr": "fr", "fr-ca": "fr", "fr-be": "fr", "fr-ch": "fr",
    "french": "fr", "francais": "fr", "français": "fr",

    # Anglais
    "en": "en", "en-us": "en", "en-gb": "en", "en-ca": "en", "en-au": "en",
    "english": "en", "anglais": "en",

    # Espagnol
    "es": "es", "es-es": "es", "es-mx": "es", "es-ar": "es",
    "spanish": "es", "espanol": "es", "español": "es",

    # Allemand
    "de": "de", "de-de": "de", "de-at": "de", "de-ch": "de",
    "german": "de", "deutsch": "de", "allemand": "de",

    # Portugais
    "pt": "pt", "pt-br": "pt", "pt-pt": "pt",
    "portuguese": "pt", "portugues": "pt", "português": "pt",

    # Italien
    "it": "it", "it-it": "it", "italian": "it", "italiano": "it",

    # Néerlandais
    "nl": "nl", "nl-nl": "nl", "nl-be": "nl", "dutch": "nl", "nederlands": "nl",

    # Russe
    "ru": "ru", "ru-ru": "ru", "russian": "ru", "russe": "ru",

    # Chinois
    "zh": "zh", "zh-cn": "zh", "zh-tw": "zh", "chinese": "zh", "chinois": "zh",

    # Japonais
    "ja": "ja", "ja-jp": "ja", "japanese": "ja", "japonais": "ja",

    # Coréen
    "ko": "ko", "ko-kr": "ko", "korean": "ko", "coréen": "ko",

    # Arabe
    "ar": "ar", "ar-sa": "ar", "ar-ae": "ar", "arabic": "ar", "arabe": "ar",

    # Hindi
    "hi": "hi", "hi-in": "hi", "hindi": "hi",

    # Polonais
    "pl": "pl", "pl-pl": "pl", "polish": "pl", "polonais": "pl",

    # Turc
    "tr": "tr", "tr-tr": "tr", "turkish": "tr", "turc": "tr",

    # Suédois
    "sv": "sv", "sv-se": "sv", "swedish": "sv", "suédois": "sv",

    # Norvégien
    "no": "no", "nb": "no", "no-no": "no", "norwegian": "no", "norvégien": "no",

    # Danois
    "da": "da", "da-dk": "da", "danish": "da", "danois": "da",

    # Finnois
    "fi": "fi", "fi-fi": "fi", "finnish": "fi", "finnois": "fi",

    # Tchèque
    "cs": "cs", "cs-cz": "cs", "czech": "cs", "tchèque": "cs",

    # Hongrois
    "hu": "hu", "hu-hu": "hu", "hungarian": "hu", "hongrois": "hu",

    # Roumain
    "ro": "ro", "ro-ro": "ro", "romanian": "ro", "roumain": "ro",

    # Grec
    "el": "el", "el-gr": "el", "greek": "el", "grec": "el",

    # Hébreu
    "he": "he", "he-il": "he", "hebrew": "he", "hébreu": "he",

    # Thaï
    "th": "th", "th-th": "th", "thai": "th", "thaï": "th",

    # Vietnamien
    "vi": "vi", "vi-vn": "vi", "vietnamese": "vi", "vietnamien": "vi",

    # Indonésien
    "id": "id", "id-id": "id", "indonesian": "id", "indonésien": "id",

    # Malais
    "ms": "ms", "ms-my": "ms", "malay": "ms", "malais": "ms",
}

COUNTRY_CODES = {
    # Europe
    "fr": "france", "france": "france", "french": "france",
    "uk": "united-kingdom", "gb": "united-kingdom", "united-kingdom": "united-kingdom",
    "england": "united-kingdom", "scotland": "united-kingdom", "wales": "united-kingdom",
    "de": "germany", "germany": "germany", "deutschland": "germany", "allemagne": "germany",
    "es": "spain", "spain": "spain", "espana": "spain", "españa": "spain", "espagne": "spain",
    "it": "italy", "italy": "italy", "italia": "italy", "italie": "italy",
    "pt": "portugal", "portugal": "portugal",
    "nl": "netherlands", "netherlands": "netherlands", "holland": "netherlands", "pays-bas": "netherlands",
    "be": "belgium", "belgium": "belgium", "belgique": "belgium",
    "ch": "switzerland", "switzerland": "switzerland", "suisse": "switzerland",
    "at": "austria", "austria": "austria", "autriche": "austria",
    "se": "sweden", "sweden": "sweden", "suède": "sweden",
    "no": "norway", "norway": "norway", "norvège": "norway",
    "dk": "denmark", "denmark": "denmark", "danemark": "denmark",
    "fi": "finland", "finland": "finland", "finlande": "finland",
    "pl": "poland", "poland": "poland", "pologne": "poland",
    "cz": "czech-republic", "czech": "czech-republic", "czechia": "czech-republic",
    "hu": "hungary", "hungary": "hungary", "hongrie": "hungary",
    "ro": "romania", "romania": "romania", "roumanie": "romania",
    "gr": "greece", "greece": "greece", "grèce": "greece",
    "ie": "ireland", "ireland": "ireland", "irlande": "ireland",
    "tr": "turkey", "turkey": "turkey", "turquie": "turkey",
    "ru": "russia", "russia": "russia", "russie": "russia",

    # Amérique du Nord
    "us": "usa", "usa": "usa", "united-states": "usa", "america": "usa",
    "états-unis": "usa", "etats-unis": "usa",
    "ca": "canada", "canada": "canada",
    "mx": "mexico", "mexico": "mexico", "mexique": "mexico",

    # Amérique du Sud
    "br": "brazil", "brazil": "brazil", "brasil": "brazil", "brésil": "brazil",
    "ar": "argentina", "argentina": "argentina", "argentine": "argentina",
    "cl": "chile", "chile": "chile", "chili": "chile",
    "co": "colombia", "colombia": "colombia", "colombie": "colombia",
    "pe": "peru", "peru": "peru", "pérou": "peru",
    "ve": "venezuela", "venezuela": "venezuela",
    "ec": "ecuador", "ecuador": "ecuador", "équateur": "ecuador",
    "uy": "uruguay", "uruguay": "uruguay",

    # Asie
    "cn": "china", "china": "china", "chine": "china",
    "jp": "japan", "japan": "japan", "japon": "japan",
    "kr": "south-korea", "south-korea": "south-korea", "korea": "south-korea", "corée": "south-korea",
    "in": "india", "india": "india", "inde": "india",
    "th": "thailand", "thailand": "thailand", "thaïlande": "thailand",
    "vn": "vietnam", "vietnam": "vietnam",
    "id": "indonesia", "indonesia": "indonesia", "indonésie": "indonesia",
    "my": "malaysia", "malaysia": "malaysia", "malaisie": "malaysia",
    "sg": "singapore", "singapore": "singapore", "singapour": "singapore",
    "ph": "philippines", "philippines": "philippines",
    "pk": "pakistan", "pakistan": "pakistan",
    "bd": "bangladesh", "bangladesh": "bangladesh",
    "il": "israel", "israel": "israel", "israël": "israel",
    "ae": "uae", "uae": "uae", "emirates": "uae", "dubai": "uae", "émirats": "uae",
    "sa": "saudi-arabia", "saudi": "saudi-arabia", "arabie": "saudi-arabia",

    # Océanie
    "au": "australia", "australia": "australia", "australie": "australia",
    "nz": "new-zealand", "new-zealand": "new-zealand", "nouvelle-zélande": "new-zealand",

    # Afrique
    "za": "south-africa", "south-africa": "south-africa", "afrique-du-sud": "south-africa",
    "eg": "egypt", "egypt": "egypt", "égypte": "egypt",
    "ma": "morocco", "morocco": "morocco", "maroc": "morocco",
    "tn": "tunisia", "tunisia": "tunisia", "tunisie": "tunisia",
    "dz": "algeria", "algeria": "algeria", "algérie": "algeria",
    "ke": "kenya", "kenya": "kenya",
    "ng": "nigeria", "nigeria": "nigeria", "nigéria": "nigeria",
}

REGION_KEYWORDS = {
    "europe": ["europe", "european", "eu", "européen", "européenne"],
    "asia": ["asia", "asian", "asie", "asiatique"],
    "africa": ["africa", "african", "afrique", "africain", "africaine"],
    "americas": ["america", "americas", "américas", "amérique", "américain", "américaine"],
    "north-america": ["north-america", "amérique-du-nord", "amérique du nord"],
    "south-america": ["south-america", "amérique-du-sud", "amérique du sud", "amérique-latine"],
    "oceania": ["oceania", "pacific", "océanie", "pacifique"],
    "middle-east": ["middle-east", "moyen-orient", "proche-orient"],
}

# Pays par région (pour inférence)
COUNTRIES_BY_REGION = {
    "europe": [
        "france", "germany", "spain", "italy", "united-kingdom", "netherlands",
        "belgium", "switzerland", "austria", "sweden", "norway", "denmark",
        "finland", "poland", "czech-republic", "hungary", "romania", "greece",
        "ireland", "portugal"
    ],
    "asia": [
        "china", "japan", "south-korea", "india", "thailand", "vietnam",
        "indonesia", "malaysia", "singapore", "philippines", "pakistan",
        "bangladesh"
    ],
    "africa": [
        "south-africa", "egypt", "morocco", "tunisia", "algeria", "kenya", "nigeria"
    ],
    "americas": [
        "usa", "canada", "mexico", "brazil", "argentina", "chile", "colombia",
        "peru", "venezuela", "ecuador", "uruguay"
    ],
    "oceania": [
        "australia", "new-zealand"
    ],
    "middle-east": [
        "israel", "uae", "saudi-arabia", "turkey"
    ]
}

CATEGORY_KEYWORDS = {
    # Catégories générales
    "guide": ["guide", "how-to", "tutorial", "tutoriel", "conseils", "tips"],
    "news": ["news", "actualite", "actualité", "nouvelles", "info"],
    "lifestyle": ["lifestyle", "style-de-vie", "vie", "living"],
    "travel": ["travel", "voyage", "trip", "destination", "tourism", "tourisme"],
    "work": ["work", "travail", "job", "emploi", "career", "carrière"],
    "housing": ["housing", "logement", "accommodation", "rent", "location", "apartment"],
    "health": ["health", "santé", "medical", "médical", "healthcare"],
    "finance": ["finance", "money", "argent", "banking", "banque", "tax", "impot"],
    "education": ["education", "école", "school", "university", "université", "étude"],
    "culture": ["culture", "art", "museum", "musée", "heritage", "patrimoine"],
    "food": ["food", "cuisine", "restaurant", "gastronomie", "cooking"],
    "tech": ["tech", "technology", "technologie", "digital", "numérique", "it"],
    "business": ["business", "entreprise", "company", "société", "commerce"],
    "legal": ["legal", "juridique", "law", "droit", "visa", "immigration"],
    "sports": ["sport", "sports", "fitness", "gym"],
    "entertainment": ["entertainment", "divertissement", "cinema", "cinéma", "tv", "music"],
}

# ============================================================================
# REGEX PATTERNS COMPILÉS (PERFORMANCE)
# ============================================================================

# Langue dans URL: /fr/, /en-us/, /de/, etc.
LANG_URL_PATTERN = re.compile(
    r'/(' + '|'.join(re.escape(k) for k in LANGUAGE_CODES.keys() if '-' in k or len(k) == 2) + r')(?:/|$)',
    re.IGNORECASE
)

# Catégorie dans URL: /category/tech/, /categorie/voyages/, etc.
CATEGORY_URL_PATTERN = re.compile(
    r'/(category|categorie|rubrique|section)/([^/]+)',
    re.IGNORECASE
)

# Date dans URL: /2024/01/, /2024-01-15/
DATE_URL_PATTERN = re.compile(
    r'/(\d{4})[/-](\d{2})(?:[/-](\d{2}))?'
)

# Pays/Région dans URL
COUNTRY_URL_PATTERN = re.compile(
    r'/(' + '|'.join(re.escape(c) for c in COUNTRY_CODES.keys() if len(c) > 2) + r')(?:/|$)',
    re.IGNORECASE
)


# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================

class MetadataExtractor:
    """
    Extracteur universel de métadonnées pour articles de blog.
    Fonctionne sur n'importe quel site web.

    Usage:
        extractor = MetadataExtractor()
        metadata = extractor.extract_all(url, response)
    """

    def __init__(self, enable_content_detection: bool = True):
        """
        Initialise l'extracteur.

        Args:
            enable_content_detection: Active la détection depuis le contenu (peut être lent)
        """
        self.enable_content_detection = enable_content_detection

        # Détection de langue (import lazy)
        self._langdetect_available = None

    def extract_all(self, url: str, response: Any, content_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Extrait toutes les métadonnées possibles depuis une page web.

        Args:
            url: URL de la page
            response: Objet Scrapy Response
            content_text: Texte du contenu (optionnel, pour détection langue)

        Returns:
            dict: {
                "language": "fr",
                "country": "france",
                "region": "europe",
                "category": "guide",
                "subcategory": "logement",
                "city": "paris",
                "year": 2024,
                "month": 1,
                "day": 15,
                "confidence": {"language": 0.9, "country": 0.8, ...}
            }
        """
        metadata: Dict[str, Any] = {}
        confidence: Dict[str, float] = {}

        # 1. Extraction depuis URL (haute confiance)
        url_meta = self.extract_from_url(url)
        metadata.update(url_meta)
        for key in url_meta:
            confidence[key] = 0.9

        # 2. Extraction depuis breadcrumbs (confiance moyenne-haute)
        breadcrumb_meta = self.extract_from_breadcrumbs(response)
        for key, value in breadcrumb_meta.items():
            if not metadata.get(key):
                metadata[key] = value
                confidence[key] = 0.8

        # 3. Extraction depuis Schema.org (haute confiance)
        schema_meta = self.extract_from_schema_org(response)
        for key, value in schema_meta.items():
            if not metadata.get(key):
                metadata[key] = value
                confidence[key] = 0.85

        # 4. Extraction depuis meta tags (confiance moyenne)
        meta_tags_meta = self.extract_from_meta_tags(response)
        for key, value in meta_tags_meta.items():
            if not metadata.get(key):
                metadata[key] = value
                confidence[key] = 0.7

        # 5. Extraction depuis contenu (fallback, basse confiance)
        if self.enable_content_detection and content_text:
            content_meta = self.extract_from_content(content_text)
            for key, value in content_meta.items():
                if not metadata.get(key):
                    metadata[key] = value
                    confidence[key] = 0.5

        # 6. Normalisation finale
        metadata = self.normalize_metadata(metadata)

        # 7. Inférence de région depuis pays
        if metadata.get("country") and not metadata.get("region"):
            metadata["region"] = self._infer_region_from_country(metadata["country"])
            confidence["region"] = 0.95

        # Ajout des scores de confiance
        metadata["confidence"] = confidence

        logger.debug(f"Extracted metadata for {url}: {metadata}")

        return metadata

    # ========================================================================
    # EXTRACTION DEPUIS URL
    # ========================================================================

    def extract_from_url(self, url: str) -> Dict[str, Any]:
        """
        Parse l'URL pour extraire métadonnées (langue, pays, catégorie, date).

        Args:
            url: URL à parser

        Returns:
            dict: Métadonnées extraites
        """
        metadata: Dict[str, Any] = {}
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Langue
        lang_match = LANG_URL_PATTERN.search(path)
        if lang_match:
            lang_code = lang_match.group(1)
            metadata["language"] = LANGUAGE_CODES.get(lang_code, lang_code)

            # Inférer pays depuis langue (ex: /fr-ca/ → Canada)
            if "-" in lang_code:
                country_part = lang_code.split("-")[1]
                if country_part in COUNTRY_CODES:
                    metadata["country"] = COUNTRY_CODES[country_part]

        # Catégorie
        cat_match = CATEGORY_URL_PATTERN.search(path)
        if cat_match:
            category_slug = cat_match.group(2).strip("-")
            metadata["category"] = self._map_category(category_slug)

        # Date
        date_match = DATE_URL_PATTERN.search(path)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            # Valider les dates (années entre 2000 et maintenant, mois 1-12)
            from datetime import datetime
            current_year = datetime.now().year
            if 2000 <= year <= current_year and 1 <= month <= 12:
                metadata["year"] = year
                metadata["month"] = month
                if date_match.group(3):
                    day = int(date_match.group(3))
                    if 1 <= day <= 31:
                        metadata["day"] = day

        # Pays (noms longs dans URL)
        country_match = COUNTRY_URL_PATTERN.search(path)
        if country_match:
            country_name = country_match.group(1)
            metadata["country"] = COUNTRY_CODES.get(country_name, country_name)

        # Région (keywords)
        for region, keywords in REGION_KEYWORDS.items():
            if any(kw in path for kw in keywords):
                metadata["region"] = region
                break

        # Ville (patterns communs)
        city = self._extract_city_from_path(path)
        if city:
            metadata["city"] = city

        return metadata

    def _extract_city_from_path(self, path: str) -> Optional[str]:
        """
        Tente d'extraire un nom de ville depuis le path.
        Pattern: /city/paris/, /ville/bangkok/, etc.
        """
        city_pattern = re.compile(r'/(city|ville|ciudad)/([a-z-]+)', re.IGNORECASE)
        match = city_pattern.search(path)
        if match:
            return match.group(2).replace("-", " ").title()
        return None

    def _map_category(self, slug: str) -> str:
        """
        Mappe un slug de catégorie vers une catégorie standard.
        """
        slug_lower = slug.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in slug_lower for kw in keywords):
                return category
        return slug  # Retour du slug original si pas de match

    # ========================================================================
    # EXTRACTION DEPUIS BREADCRUMBS
    # ========================================================================

    def extract_from_breadcrumbs(self, response: Any) -> Dict[str, Any]:
        """
        Extrait métadonnées depuis le fil d'Ariane (breadcrumbs).

        Pattern HTML:
            <nav class="breadcrumb">
              <a>Home</a> > <a>Voyages</a> > <a>Europe</a> > <a>France</a>
            </nav>

        Args:
            response: Scrapy Response

        Returns:
            dict: Métadonnées extraites
        """
        metadata: Dict[str, Any] = {}

        # Sélecteurs CSS communs pour breadcrumbs
        selectors = [
            '.breadcrumb a::text',
            '.breadcrumbs a::text',
            '[itemtype*="BreadcrumbList"] a::text',
            'nav ol li a::text',
            '.trail-items a::text',
            '.breadcrumb-item a::text',
            '#breadcrumbs a::text',
        ]

        breadcrumb_texts: List[str] = []
        for selector in selectors:
            texts = response.css(selector).getall()
            if texts:
                breadcrumb_texts = [t.strip() for t in texts if t.strip()]
                break

        if not breadcrumb_texts:
            return metadata

        # Analyse des items du breadcrumb
        for item in breadcrumb_texts:
            item_lower = item.lower()

            # Catégorie
            if not metadata.get("category"):
                for category, keywords in CATEGORY_KEYWORDS.items():
                    if any(kw in item_lower for kw in keywords):
                        metadata["category"] = category
                        break

            # Région
            if not metadata.get("region"):
                for region, keywords in REGION_KEYWORDS.items():
                    if any(kw in item_lower for kw in keywords):
                        metadata["region"] = region
                        break

            # Pays
            if not metadata.get("country"):
                country_match = self._find_country_in_text(item)
                if country_match:
                    metadata["country"] = country_match

        return metadata

    # ========================================================================
    # EXTRACTION DEPUIS SCHEMA.ORG
    # ========================================================================

    def extract_from_schema_org(self, response: Any) -> Dict[str, Any]:
        """
        Extrait métadonnées depuis JSON-LD Schema.org.

        Exemple:
            <script type="application/ld+json">
            {
              "@type": "Article",
              "articleSection": "Technology",
              "inLanguage": "fr-FR",
              "contentLocation": {"name": "Paris, France"}
            }
            </script>

        Args:
            response: Scrapy Response

        Returns:
            dict: Métadonnées extraites
        """
        metadata: Dict[str, Any] = {}

        # Extraire tous les blocs JSON-LD
        json_ld_scripts = response.css('script[type="application/ld+json"]::text').getall()

        for script in json_ld_scripts:
            try:
                data = json.loads(script)

                # Gérer les graphes (@graph)
                if isinstance(data, dict) and "@graph" in data:
                    items = data["@graph"]
                elif isinstance(data, list):
                    items = data
                else:
                    items = [data]

                for item in items if isinstance(items, list) else [items]:
                    if not isinstance(item, dict):
                        continue

                    # Article section → category
                    if not metadata.get("category") and "articleSection" in item:
                        section = item["articleSection"]
                        if isinstance(section, str):
                            metadata["category"] = self._map_category(section)

                    # Langue
                    if not metadata.get("language") and "inLanguage" in item:
                        lang = item["inLanguage"]
                        if isinstance(lang, str):
                            lang_code = lang.lower().split("-")[0]
                            metadata["language"] = LANGUAGE_CODES.get(lang_code, lang_code)

                    # Location → pays/ville
                    if "contentLocation" in item:
                        location = item["contentLocation"]
                        if isinstance(location, dict) and "name" in location:
                            location_name = location["name"]
                            country = self._find_country_in_text(location_name)
                            if country:
                                metadata["country"] = country
                            # Essayer d'extraire la ville
                            parts = location_name.split(",")
                            if len(parts) >= 1:
                                potential_city = parts[0].strip()
                                if len(potential_city) > 2 and not metadata.get("city"):
                                    metadata["city"] = potential_city

                    # Keywords/tags
                    if "keywords" in item:
                        keywords = item["keywords"]
                        if isinstance(keywords, str):
                            keywords = [k.strip() for k in keywords.split(",")]
                        if isinstance(keywords, list) and not metadata.get("category"):
                            for kw in keywords:
                                cat = self._map_category(kw)
                                if cat != kw.lower():  # Match trouvé (comparer en lowercase)
                                    metadata["category"] = cat
                                    break

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"Failed to parse JSON-LD: {e}")
                continue

        return metadata

    # ========================================================================
    # EXTRACTION DEPUIS META TAGS
    # ========================================================================

    def extract_from_meta_tags(self, response: Any) -> Dict[str, Any]:
        """
        Extrait métadonnées depuis les balises <meta>.

        Tags supportés:
            <meta property="article:section" content="Business" />
            <meta property="og:locale" content="fr_FR" />
            <meta name="geo.region" content="FR-75" />
            <meta name="geo.placename" content="Paris" />
            <meta property="article:tag" content="Travel,Europe,France" />

        Args:
            response: Scrapy Response

        Returns:
            dict: Métadonnées extraites
        """
        metadata: Dict[str, Any] = {}

        # Article section
        article_section = (
            response.css('meta[property="article:section"]::attr(content)').get()
            or response.css('meta[name="article:section"]::attr(content)').get()
        )
        if article_section and not metadata.get("category"):
            metadata["category"] = self._map_category(article_section)

        # Locale (langue)
        locale = (
            response.css('meta[property="og:locale"]::attr(content)').get()
            or response.css('meta[name="locale"]::attr(content)').get()
        )
        if locale and not metadata.get("language"):
            lang_code = locale.lower().replace("_", "-").split("-")[0]
            metadata["language"] = LANGUAGE_CODES.get(lang_code, lang_code)

        # Geo region
        geo_region = response.css('meta[name="geo.region"]::attr(content)').get()
        if geo_region and not metadata.get("country"):
            # Format: FR-75 (ISO code)
            country_code = geo_region.split("-")[0].lower()
            metadata["country"] = COUNTRY_CODES.get(country_code)

        # Geo placename (ville)
        geo_place = response.css('meta[name="geo.placename"]::attr(content)').get()
        if geo_place and not metadata.get("city"):
            metadata["city"] = geo_place.strip()

        # Article tags
        article_tags = (
            response.css('meta[property="article:tag"]::attr(content)').get()
            or response.css('meta[name="keywords"]::attr(content)').get()
        )
        if article_tags:
            tags = [t.strip() for t in article_tags.split(",")]
            for tag in tags:
                tag_lower = tag.lower()

                # Chercher catégorie
                if not metadata.get("category"):
                    cat = self._map_category(tag_lower)
                    if cat != tag_lower:
                        metadata["category"] = cat

                # Chercher pays
                if not metadata.get("country"):
                    country = self._find_country_in_text(tag_lower)
                    if country:
                        metadata["country"] = country

                # Chercher région
                if not metadata.get("region"):
                    for region, keywords in REGION_KEYWORDS.items():
                        if any(kw in tag_lower for kw in keywords):
                            metadata["region"] = region
                            break

        return metadata

    # ========================================================================
    # EXTRACTION DEPUIS CONTENU (FALLBACK)
    # ========================================================================

    def extract_from_content(self, text: str) -> Dict[str, Any]:
        """
        Détecte langue et extrait pays depuis le contenu texte.

        Args:
            text: Contenu textuel de l'article

        Returns:
            dict: Métadonnées extraites
        """
        metadata: Dict[str, Any] = {}

        # Détection de langue via langdetect
        if self._is_langdetect_available():
            try:
                from langdetect import detect
                detected_lang = detect(text[:1000])  # Premier 1000 chars
                metadata["language"] = LANGUAGE_CODES.get(detected_lang, detected_lang)
            except Exception as e:
                logger.debug(f"Language detection failed: {e}")

        # Extraction pays depuis texte (mentions fréquentes)
        country = self._find_country_in_text(text[:2000])  # Premiers 2000 chars
        if country:
            metadata["country"] = country

        return metadata

    def _is_langdetect_available(self) -> bool:
        """Vérifie si langdetect est disponible (lazy check)."""
        if self._langdetect_available is None:
            try:
                import langdetect
                self._langdetect_available = True
            except ImportError:
                self._langdetect_available = False
                logger.debug("langdetect not installed, skipping language detection from content")
        return self._langdetect_available

    # ========================================================================
    # NORMALISATION & HELPERS
    # ========================================================================

    def normalize_metadata(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise les valeurs des métadonnées (lowercase, mapping codes).

        Args:
            raw: Métadonnées brutes

        Returns:
            dict: Métadonnées normalisées
        """
        normalized = {}

        for key, value in raw.items():
            if key == "confidence":
                normalized[key] = value
                continue

            if isinstance(value, str):
                value_lower = value.lower().strip()

                # Normaliser langue
                if key == "language":
                    normalized[key] = LANGUAGE_CODES.get(value_lower, value_lower)

                # Normaliser pays
                elif key == "country":
                    normalized[key] = COUNTRY_CODES.get(value_lower, value_lower)

                # Normaliser catégorie
                elif key == "category":
                    normalized[key] = self._map_category(value_lower)

                else:
                    normalized[key] = value_lower
            else:
                normalized[key] = value

        return normalized

    def _find_country_in_text(self, text: str) -> Optional[str]:
        """
        Trouve le pays mentionné dans un texte via pattern matching.

        Args:
            text: Texte à analyser

        Returns:
            str: Code pays normalisé ou None
        """
        text_lower = text.lower()

        # Chercher les noms longs en priorité (éviter faux positifs)
        # Traiter "united states" et "united kingdom" comme cas spéciaux (avec espace)
        for country_name, country_code in sorted(
            COUNTRY_CODES.items(),
            key=lambda x: len(x[0]),
            reverse=True
        ):
            # Pour noms > 3 chars OU noms avec tirets (comme "united-states")
            if len(country_name) > 3 or "-" in country_name:
                # Chercher aussi la version avec espaces (united-states → united states)
                pattern_hyphen = r'\b' + re.escape(country_name) + r'\b'
                pattern_space = r'\b' + re.escape(country_name.replace("-", " ")) + r'\b'
                if re.search(pattern_hyphen, text_lower) or re.search(pattern_space, text_lower):
                    return country_code

        return None

    def _infer_region_from_country(self, country: str) -> Optional[str]:
        """
        Infère la région géographique depuis le pays.

        Args:
            country: Code pays

        Returns:
            str: Code région ou None
        """
        for region, countries in COUNTRIES_BY_REGION.items():
            if country in countries:
                return region
        return None
