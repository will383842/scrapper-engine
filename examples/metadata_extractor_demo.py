"""
Démonstration de MetadataExtractor - Extracteur Universel de Métadonnées.

Ce script montre comment utiliser MetadataExtractor pour extraire
automatiquement langue, pays, catégorie, région depuis des URLs.

Usage:
    python examples/metadata_extractor_demo.py
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer scraper
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.utils.metadata_extractor import MetadataExtractor


def print_metadata(url: str, metadata: dict):
    """Affiche joliment les métadonnées extraites."""
    print(f"\n{'='*80}")
    print(f"URL: {url}")
    print(f"{'='*80}")

    if not metadata or all(v is None for k, v in metadata.items() if k != "confidence"):
        print("[X] Aucune métadonnée extraite")
        return

    # Afficher métadonnées
    fields = ["language", "country", "region", "category", "subcategory", "city", "year", "month", "day"]
    for field in fields:
        value = metadata.get(field)
        if value is not None:
            confidence = metadata.get("confidence", {}).get(field, "N/A")
            emoji = "[OK]" if isinstance(confidence, (int, float)) and confidence > 0.7 else "[!]"
            print(f"{emoji} {field.capitalize():<12}: {value} (confiance: {confidence})")

    print("-" * 80)


def demo_url_patterns():
    """Démonstration extraction depuis patterns URL variés."""
    print("\n" + "="*80)
    print("DÉMO 1: EXTRACTION DEPUIS PATTERNS URL")
    print("="*80)

    extractor = MetadataExtractor()

    urls = [
        # Blog expat
        "https://expatblog.com/fr/europe/france/category/housing/2024/01/paris-apartments",

        # Tech blog
        "https://techblog.com/en-us/category/technology/2024/02/ai-trends",

        # Site expat.com
        "https://www.expat.com/en/guide/europe/spain/barcelona/living-in-barcelona.html",

        # Blog voyage
        "https://travelblog.com/de/asia/thailand/category/travel/2024/03/bangkok-guide",

        # Blog lifestyle
        "https://lifestyleblog.com/pt-br/americas/brazil/2024/04/sao-paulo-life",
    ]

    for url in urls:
        metadata = extractor.extract_from_url(url)
        print_metadata(url, metadata)


def demo_with_mock_response():
    """Démonstration avec mock Scrapy Response (simulation)."""
    print("\n" + "="*80)
    print("DÉMO 2: EXTRACTION DEPUIS MOCK RESPONSE (SIMULATION)")
    print("="*80)

    from unittest.mock import Mock

    extractor = MetadataExtractor()

    # Simulation d'une response Scrapy
    url = "https://blog.example.com/article-paris"
    response = Mock()

    def css_mock(selector):
        """Mock CSS selector."""
        mock_result = Mock()

        # Breadcrumbs
        if ".breadcrumb" in selector:
            mock_result.getall.return_value = ["Home", "Travel", "Europe", "France"]

        # Meta tags
        elif "meta[property='article:section']" in selector:
            mock_result.get.return_value = "Travel"
        elif "meta[property='og:locale']" in selector:
            mock_result.get.return_value = "fr_FR"
        elif "meta[name='geo.placename']" in selector:
            mock_result.get.return_value = "Paris"

        # Schema.org
        elif 'script[type="application/ld+json"]' in selector:
            schema_json = '''
            {
                "@type": "Article",
                "articleSection": "Travel",
                "inLanguage": "fr-FR",
                "contentLocation": {"name": "Paris, France"}
            }
            '''
            mock_result.getall.return_value = [schema_json]

        else:
            mock_result.get.return_value = None
            mock_result.getall.return_value = []

        return mock_result

    response.css = css_mock

    # Extraction complète
    metadata = extractor.extract_all(url, response)
    print_metadata(url, metadata)


def demo_content_detection():
    """Démonstration détection depuis contenu texte."""
    print("\n" + "="*80)
    print("DÉMO 3: DÉTECTION DEPUIS CONTENU TEXTE")
    print("="*80)

    extractor = MetadataExtractor(enable_content_detection=True)

    texts = [
        (
            "Living in Thailand is an amazing experience. Bangkok offers "
            "a great quality of life and the people are very friendly. "
            "Thailand has become a popular destination for expats.",
            "Texte en anglais sur la Thaïlande"
        ),
        (
            "Vivre en France est une expérience incroyable. Paris offre "
            "une qualité de vie exceptionnelle et les gens sont accueillants. "
            "La France est devenue une destination populaire.",
            "Texte en français sur la France"
        ),
        (
            "Leben in Deutschland ist toll. Berlin bietet viele Möglichkeiten "
            "und die Menschen sind freundlich. Deutschland ist sehr attraktiv.",
            "Texte en allemand sur l'Allemagne"
        )
    ]

    for text, description in texts:
        print(f"\n{'-'*80}")
        print(f"Texte: {description}")
        print(f"{'-'*80}")

        metadata = extractor.extract_from_content(text)

        if metadata.get("language"):
            print(f"[OK] Langue détectée: {metadata['language']}")
        else:
            print("[!] Langue non détectée (langdetect non installé?)")

        if metadata.get("country"):
            print(f"[OK] Pays détecté: {metadata['country']}")
        else:
            print("[!] Pays non détecté")


def demo_normalization():
    """Démonstration normalisation des métadonnées."""
    print("\n" + "="*80)
    print("DÉMO 4: NORMALISATION AUTOMATIQUE")
    print("="*80)

    extractor = MetadataExtractor()

    test_cases = [
        {"language": "FR-FR", "country": "FRANCE"},
        {"language": "en-us", "country": "United States"},
        {"language": "DE", "country": "Deutschland"},
        {"category": "TRAVEL", "region": "EUROPE"}
    ]

    for raw in test_cases:
        normalized = extractor.normalize_metadata(raw)
        print(f"\nRaw:        {raw}")
        print(f"Normalized: {normalized}")


def demo_region_inference():
    """Démonstration inférence de région depuis pays."""
    print("\n" + "="*80)
    print("DÉMO 5: INFÉRENCE DE RÉGION DEPUIS PAYS")
    print("="*80)

    extractor = MetadataExtractor()

    countries = [
        "france",
        "germany",
        "spain",
        "thailand",
        "japan",
        "usa",
        "canada",
        "brazil",
        "australia",
        "morocco"
    ]

    print(f"\n{'Pays':<15} -> {'Region'}")
    print("-" * 40)

    for country in countries:
        region = extractor._infer_region_from_country(country)
        if region:
            print(f"{country:<15} -> {region}")
        else:
            print(f"{country:<15} -> (non trouve)")


def demo_real_world_scenarios():
    """Scénarios réels d'utilisation."""
    print("\n" + "="*80)
    print("DÉMO 6: SCÉNARIOS RÉELS")
    print("="*80)

    from unittest.mock import Mock

    extractor = MetadataExtractor(enable_content_detection=True)

    # Scénario 1: Blog expat complet
    print("\n" + "-"*80)
    print("Scénario 1: Article blog expat sur logement à Barcelone")
    print("-"*80)

    url1 = "https://expatblog.com/fr/europe/spain/category/housing/2024/01/barcelona-apartments"
    response1 = Mock()

    def css_mock1(selector):
        mock_result = Mock()
        mock_result.get.return_value = None
        mock_result.getall.return_value = []
        return mock_result

    response1.css = css_mock1
    content1 = """
    Finding an apartment in Barcelona, Spain can be challenging.
    The housing market in Barcelona is competitive but offers great options
    for expats looking to settle in this beautiful European city.
    """

    metadata1 = extractor.extract_all(url1, response1, content1)
    print_metadata(url1, metadata1)

    # Scénario 2: Blog tech US
    print("\n" + "-"*80)
    print("Scénario 2: Article tech blog sur IA")
    print("-"*80)

    url2 = "https://techcrunch.com/en-us/category/artificial-intelligence/2024/02/ai-trends"
    response2 = Mock()

    def css_mock2(selector):
        mock_result = Mock()
        mock_result.get.return_value = None
        mock_result.getall.return_value = []
        return mock_result

    response2.css = css_mock2

    metadata2 = extractor.extract_all(url2, response2)
    print_metadata(url2, metadata2)


def main():
    """Point d'entrée principal."""
    print("\n" + "="*80)
    print("METADATA EXTRACTOR - DÉMONSTRATION COMPLÈTE")
    print("="*80)

    # Lancer toutes les démos
    demo_url_patterns()
    demo_with_mock_response()
    demo_content_detection()
    demo_normalization()
    demo_region_inference()
    demo_real_world_scenarios()

    print("\n" + "="*80)
    print("DEMONSTRATION TERMINEE")
    print("="*80)
    print("\nPour plus d'infos: voir scraper/utils/README_METADATA_EXTRACTOR.md")
    print("Tests: pytest tests/test_metadata_extractor.py -v\n")


if __name__ == "__main__":
    main()
