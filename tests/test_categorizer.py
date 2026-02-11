"""Tests for the contact categorization module."""

from scraper.modules.categorizer import categorize, determine_platform, generate_tags


class TestCategorize:
    def test_avocat_by_keyword(self):
        contact = {"keywords": "avocat international paris", "source_type": "google_search"}
        assert categorize(contact) == "avocat"

    def test_assureur_by_keyword(self):
        contact = {"keywords": "assurance expat", "source_type": "google_search"}
        assert categorize(contact) == "assureur"

    def test_blogueur_by_keyword(self):
        contact = {"keywords": "travel blog expat", "source_type": "google_search"}
        assert categorize(contact) == "blogueur"

    def test_no_match_returns_autre(self):
        contact = {"keywords": "random stuff", "source_type": "custom_urls"}
        assert categorize(contact) == "autre"

    def test_empty_contact(self):
        assert categorize({}) == "autre"


class TestDeterminePlatform:
    def test_sos_expat_categories(self):
        assert determine_platform("avocat") == "sos-expat"
        assert determine_platform("assureur") == "sos-expat"
        assert determine_platform("notaire") == "sos-expat"
        assert determine_platform("medecin") == "sos-expat"

    def test_ulixai_categories(self):
        assert determine_platform("blogueur") == "ulixai"
        assert determine_platform("influenceur") == "ulixai"
        assert determine_platform("admin_groupe") == "ulixai"

    def test_unknown_defaults_to_sos_expat(self):
        assert determine_platform("autre") == "sos-expat"
        assert determine_platform("unknown") == "sos-expat"


class TestGenerateTags:
    def test_basic_tags(self):
        contact = {"source_type": "google_search", "country": "FR"}
        tags = generate_tags(contact, "avocat")
        assert "avocat" in tags
        assert "google_search" in tags
        assert "fr" in tags

    def test_no_country(self):
        contact = {"source_type": "google_maps"}
        tags = generate_tags(contact, "blogueur")
        assert "blogueur" in tags
        assert "google_maps" in tags
