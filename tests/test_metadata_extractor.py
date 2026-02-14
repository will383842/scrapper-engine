"""
Tests unitaires pour MetadataExtractor.

Tests l'extraction de métadonnées depuis:
- URLs (expat.com, blogs génériques)
- Breadcrumbs
- Schema.org JSON-LD
- Meta tags
- Contenu texte

Run with: python -m pytest tests/test_metadata_extractor.py -v
"""

import json
from unittest.mock import Mock
import pytest

from scraper.utils.metadata_extractor import MetadataExtractor


class TestMetadataExtractorURL:
    """Tests extraction depuis URLs."""

    def setup_method(self):
        self.extractor = MetadataExtractor()

    def test_extract_language_from_url(self):
        """Test extraction de langue depuis URL."""
        # Français
        meta = self.extractor.extract_from_url("https://example.com/fr/article")
        assert meta["language"] == "fr"

        # Anglais US
        meta = self.extractor.extract_from_url("https://example.com/en-us/blog")
        assert meta["language"] == "en"
        assert meta["country"] == "usa"

        # Allemand
        meta = self.extractor.extract_from_url("https://example.com/de/news")
        assert meta["language"] == "de"

    def test_extract_country_from_url(self):
        """Test extraction de pays depuis URL."""
        # France
        meta = self.extractor.extract_from_url("https://example.com/france/paris")
        assert meta["country"] == "france"

        # Spain
        meta = self.extractor.extract_from_url("https://example.com/spain/barcelona")
        assert meta["country"] == "spain"

        # Thailand
        meta = self.extractor.extract_from_url("https://blog.com/thailand/travel")
        assert meta["country"] == "thailand"

    def test_extract_category_from_url(self):
        """Test extraction de catégorie depuis URL."""
        # Pattern /category/
        meta = self.extractor.extract_from_url("https://blog.com/category/travel")
        assert meta["category"] == "travel"

        # Pattern /categorie/ (français)
        meta = self.extractor.extract_from_url("https://blog.fr/categorie/logement")
        assert meta["category"] == "housing"

        # Pattern /rubrique/
        meta = self.extractor.extract_from_url("https://news.com/rubrique/finance")
        assert meta["category"] == "finance"

    def test_extract_date_from_url(self):
        """Test extraction de date depuis URL."""
        # Format YYYY/MM
        meta = self.extractor.extract_from_url("https://blog.com/2024/01/article")
        assert meta["year"] == 2024
        assert meta["month"] == 1

        # Format YYYY-MM-DD
        meta = self.extractor.extract_from_url("https://blog.com/2024-01-15-post")
        assert meta["year"] == 2024
        assert meta["month"] == 1
        assert meta["day"] == 15

    def test_extract_region_from_url(self):
        """Test extraction de région depuis URL."""
        meta = self.extractor.extract_from_url("https://blog.com/europe/travel")
        assert meta["region"] == "europe"

        meta = self.extractor.extract_from_url("https://blog.com/asia/guides")
        assert meta["region"] == "asia"

    def test_expat_com_url_pattern(self):
        """Test pattern URL expat.com."""
        url = "https://www.expat.com/en/guide/europe/france/paris/16029-living-in-paris.html"
        meta = self.extractor.extract_from_url(url)

        assert meta["language"] == "en"
        assert meta["region"] == "europe"
        assert meta["country"] == "france"

    def test_complex_url_all_metadata(self):
        """Test extraction complète depuis URL complexe."""
        url = "https://blog.com/fr/europe/spain/category/travel/2024/01/barcelona-guide"
        meta = self.extractor.extract_from_url(url)

        assert meta["language"] == "fr"
        assert meta["region"] == "europe"
        assert meta["country"] == "spain"
        assert meta["category"] == "travel"
        assert meta["year"] == 2024
        assert meta["month"] == 1


class TestMetadataExtractorBreadcrumbs:
    """Tests extraction depuis breadcrumbs."""

    def setup_method(self):
        self.extractor = MetadataExtractor()

    def test_extract_from_simple_breadcrumbs(self):
        """Test extraction depuis breadcrumbs simple."""
        # Mock Scrapy Response
        response = Mock()
        response.css = Mock(side_effect=lambda sel: MockCSSSelector([
            "Home", "Travel", "Europe", "France"
        ]) if ".breadcrumb" in sel else MockCSSSelector([]))

        meta = self.extractor.extract_from_breadcrumbs(response)

        assert meta["category"] == "travel"
        assert meta["region"] == "europe"
        assert meta["country"] == "france"

    def test_extract_from_breadcrumbs_with_category(self):
        """Test extraction catégorie depuis breadcrumbs."""
        response = Mock()
        response.css = Mock(side_effect=lambda sel: MockCSSSelector([
            "Home", "Housing", "Rent", "Paris"
        ]) if ".breadcrumb" in sel else MockCSSSelector([]))

        meta = self.extractor.extract_from_breadcrumbs(response)

        assert meta["category"] == "housing"

    def test_no_breadcrumbs(self):
        """Test quand pas de breadcrumbs."""
        response = Mock()
        response.css = Mock(return_value=MockCSSSelector([]))

        meta = self.extractor.extract_from_breadcrumbs(response)

        assert meta == {}


class TestMetadataExtractorSchemaOrg:
    """Tests extraction depuis Schema.org JSON-LD."""

    def setup_method(self):
        self.extractor = MetadataExtractor()

    def test_extract_from_schema_org_article(self):
        """Test extraction depuis Schema.org Article."""
        schema_data = {
            "@context": "https://schema.org",
            "@type": "Article",
            "articleSection": "Technology",
            "inLanguage": "fr-FR",
            "contentLocation": {
                "name": "Paris, France"
            }
        }

        response = Mock()
        response.css = Mock(return_value=MockCSSSelector([
            json.dumps(schema_data)
        ]))

        meta = self.extractor.extract_from_schema_org(response)

        assert meta["category"] == "tech"
        assert meta["language"] == "fr"
        assert meta["country"] == "france"
        assert meta["city"] == "Paris"

    def test_extract_from_schema_org_with_keywords(self):
        """Test extraction depuis Schema.org avec keywords."""
        schema_data = {
            "@type": "Article",
            "keywords": "voyage, travel, europe, spain, barcelona"
        }

        response = Mock()
        response.css = Mock(return_value=MockCSSSelector([
            json.dumps(schema_data)
        ]))

        meta = self.extractor.extract_from_schema_org(response)

        # Doit extraire catégorie "travel"
        assert meta.get("category") == "travel"

    def test_extract_from_schema_org_graph(self):
        """Test extraction depuis Schema.org avec @graph."""
        schema_data = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebSite",
                    "name": "Example"
                },
                {
                    "@type": "Article",
                    "articleSection": "Finance",
                    "inLanguage": "en-US"
                }
            ]
        }

        response = Mock()
        response.css = Mock(return_value=MockCSSSelector([
            json.dumps(schema_data)
        ]))

        meta = self.extractor.extract_from_schema_org(response)

        assert meta["category"] == "finance"
        assert meta["language"] == "en"

    def test_invalid_json_ld(self):
        """Test gestion JSON-LD invalide."""
        response = Mock()
        response.css = Mock(return_value=MockCSSSelector([
            "invalid json{{{",
            ""
        ]))

        meta = self.extractor.extract_from_schema_org(response)

        assert meta == {}


class TestMetadataExtractorMetaTags:
    """Tests extraction depuis meta tags."""

    def setup_method(self):
        self.extractor = MetadataExtractor()

    def test_extract_article_section(self):
        """Test extraction article:section."""
        response = Mock()

        def css_mock(selector):
            if 'article:section' in selector:
                return MockCSSAttributeSelector("Business")
            return MockCSSAttributeSelector(None)

        response.css = css_mock

        meta = self.extractor.extract_from_meta_tags(response)

        assert meta["category"] == "business"

    def test_extract_og_locale(self):
        """Test extraction og:locale."""
        response = Mock()

        def css_mock(selector):
            if 'og:locale' in selector:
                return MockCSSAttributeSelector("fr_FR")
            return MockCSSAttributeSelector(None)

        response.css = css_mock

        meta = self.extractor.extract_from_meta_tags(response)

        assert meta["language"] == "fr"

    def test_extract_geo_tags(self):
        """Test extraction geo.region et geo.placename."""
        response = Mock()

        def css_mock(selector):
            if 'geo.region' in selector:
                return MockCSSAttributeSelector("FR-75")
            elif 'geo.placename' in selector:
                return MockCSSAttributeSelector("Paris")
            return MockCSSAttributeSelector(None)

        response.css = css_mock

        meta = self.extractor.extract_from_meta_tags(response)

        assert meta["country"] == "france"
        assert meta["city"] == "Paris"

    def test_extract_article_tags(self):
        """Test extraction article:tag."""
        response = Mock()

        def css_mock(selector):
            if 'article:tag' in selector:
                return MockCSSAttributeSelector("travel,voyage,Europe,Spain,Barcelona")
            return MockCSSAttributeSelector(None)

        response.css = css_mock

        meta = self.extractor.extract_from_meta_tags(response)

        # Doit extraire catégorie travel (premier keyword qui match)
        assert meta.get("category") == "travel"
        assert meta.get("region") == "europe"
        assert meta.get("country") == "spain"


class TestMetadataExtractorContent:
    """Tests extraction depuis contenu texte."""

    def setup_method(self):
        self.extractor = MetadataExtractor(enable_content_detection=True)

    def test_extract_country_from_content(self):
        """Test extraction pays depuis contenu."""
        text = """
        Living in Thailand is an amazing experience. Bangkok offers
        a great quality of life and the people are very friendly.
        Thailand has become a popular destination for expats.
        """

        meta = self.extractor.extract_from_content(text)

        assert meta["country"] == "thailand"

    def test_extract_language_detection(self):
        """Test détection langue (si langdetect installé)."""
        # Texte français
        text_fr = """
        Vivre en France est une expérience incroyable. Paris offre
        une qualité de vie exceptionnelle et les gens sont accueillants.
        La France est devenue une destination populaire.
        """

        meta = self.extractor.extract_from_content(text_fr)

        # Peut être 'fr' si langdetect installé, sinon vide
        if meta.get("language"):
            assert meta["language"] == "fr"

    def test_no_country_in_short_text(self):
        """Test pas de détection sur texte court."""
        text = "Hello world test example"

        meta = self.extractor.extract_from_content(text)

        assert meta.get("country") is None


class TestMetadataExtractorFullPipeline:
    """Tests pipeline complet d'extraction."""

    def setup_method(self):
        self.extractor = MetadataExtractor()

    def test_extract_all_expat_blog(self):
        """Test extraction complète blog expat."""
        url = "https://expatblog.com/fr/europe/spain/category/housing/2024/01/barcelona-apartments"

        # Mock response
        response = Mock()
        response.css = Mock(side_effect=self._mock_css_expat)

        content_text = """
        Finding an apartment in Barcelona, Spain can be challenging.
        The city offers great options in Europe for expats looking for housing.
        """

        meta = self.extractor.extract_all(url, response, content_text)

        assert meta["language"] == "fr"
        assert meta["region"] == "europe"
        assert meta["country"] == "spain"
        assert meta["category"] == "housing"
        assert meta["year"] == 2024
        assert meta["month"] == 1
        assert "confidence" in meta

    def test_extract_all_tech_blog(self):
        """Test extraction blog tech."""
        url = "https://techblog.com/en-us/category/technology/2024/02/ai-trends"

        response = Mock()
        response.css = Mock(side_effect=self._mock_css_tech)

        meta = self.extractor.extract_all(url, response)

        assert meta["language"] == "en"
        assert meta["country"] == "usa"
        assert meta["category"] == "tech"
        assert meta["year"] == 2024

    def test_region_inference_from_country(self):
        """Test inférence région depuis pays."""
        url = "https://blog.com/germany/berlin"

        response = Mock()
        response.css = Mock(return_value=MockCSSSelector([]))

        meta = self.extractor.extract_all(url, response)

        assert meta["country"] == "germany"
        assert meta["region"] == "europe"  # Inféré automatiquement

    def test_confidence_scores(self):
        """Test scores de confiance."""
        url = "https://blog.com/fr/france/paris"

        response = Mock()
        response.css = Mock(return_value=MockCSSSelector([]))

        meta = self.extractor.extract_all(url, response)

        assert "confidence" in meta
        assert meta["confidence"]["language"] == 0.9  # Depuis URL
        assert meta["confidence"]["country"] == 0.9

    def _mock_css_expat(self, selector):
        """Mock CSS selector pour blog expat."""
        if ".breadcrumb" in selector:
            return MockCSSSelector(["Home", "Europe", "Spain", "Housing"])
        elif 'script[type="application/ld+json"]' in selector:
            schema = {
                "@type": "Article",
                "articleSection": "Housing"
            }
            return MockCSSSelector([json.dumps(schema)])
        return MockCSSSelector([])

    def _mock_css_tech(self, selector):
        """Mock CSS selector pour blog tech."""
        if 'meta[property="article:section"]' in selector:
            return MockCSSAttributeSelector("Technology")
        elif 'meta[property="og:locale"]' in selector:
            return MockCSSAttributeSelector("en_US")
        return MockCSSAttributeSelector(None)


class TestMetadataExtractorNormalization:
    """Tests normalisation des métadonnées."""

    def setup_method(self):
        self.extractor = MetadataExtractor()

    def test_normalize_language(self):
        """Test normalisation codes langue."""
        raw = {
            "language": "FR-FR",
            "country": "FRANCE"
        }

        normalized = self.extractor.normalize_metadata(raw)

        assert normalized["language"] == "fr"
        assert normalized["country"] == "france"

    def test_normalize_country_aliases(self):
        """Test normalisation alias pays."""
        # USA
        assert self.extractor._find_country_in_text("united states") == "usa"
        assert self.extractor._find_country_in_text("america") == "usa"

        # UK
        assert self.extractor._find_country_in_text("united kingdom") == "united-kingdom"
        assert self.extractor._find_country_in_text("england") == "united-kingdom"

    def test_normalize_category(self):
        """Test normalisation catégorie."""
        raw = {"category": "TRAVEL"}
        normalized = self.extractor.normalize_metadata(raw)

        assert normalized["category"] == "travel"


class TestMetadataExtractorEdgeCases:
    """Tests cas limites."""

    def setup_method(self):
        self.extractor = MetadataExtractor()

    def test_empty_url(self):
        """Test URL vide."""
        meta = self.extractor.extract_from_url("")
        assert meta == {}

    def test_url_without_metadata(self):
        """Test URL sans métadonnées."""
        url = "https://example.com/page123"
        meta = self.extractor.extract_from_url(url)

        # Peut être vide ou avoir quelques champs
        assert isinstance(meta, dict)

    def test_multiple_countries_in_url(self):
        """Test URL avec plusieurs pays (prend le premier)."""
        url = "https://blog.com/france/germany/article"
        meta = self.extractor.extract_from_url(url)

        # Doit trouver france en premier
        assert meta["country"] == "france"

    def test_invalid_date_in_url(self):
        """Test date invalide dans URL."""
        url = "https://blog.com/9999/99/article"
        meta = self.extractor.extract_from_url(url)

        # Date invalide ignorée (année future ou mois invalide)
        assert "year" not in meta
        assert "month" not in meta


# ============================================================================
# MOCK HELPERS
# ============================================================================

class MockCSSSelector:
    """Mock pour Scrapy CSS selector retournant une liste."""

    def __init__(self, values):
        self.values = values if isinstance(values, list) else [values]

    def getall(self):
        return self.values

    def get(self):
        return self.values[0] if self.values else None


class MockCSSAttributeSelector:
    """Mock pour Scrapy CSS selector sur attribut."""

    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def getall(self):
        return [self.value] if self.value else []


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
