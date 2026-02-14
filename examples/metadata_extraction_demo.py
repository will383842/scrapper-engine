"""
Demonstration script for MetadataExtractor.

This script shows how to use the MetadataExtractor to analyze URLs
and extract geographical, temporal, and classification metadata.
"""

import sys
import io

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from scraper.utils.metadata_extractor import MetadataExtractor


def demo_url_extraction():
    """Demonstrate metadata extraction from various URLs."""
    extractor = MetadataExtractor()

    test_urls = [
        "https://expatblog.com/france/paris/visa-guide-2024/",
        "https://blog.example.com/2024/01/living-in-bangkok/",
        "https://expat.com/spain/barcelona/housing-tips/",
        "https://blog.example.com/germany/work-remote-berlin/",
        "https://expatguide.com/thailand/education-international-schools/",
        "https://blog.example.com/2024/03/uae/dubai/finance-banking/",
    ]

    print("=" * 80)
    print("URL METADATA EXTRACTION DEMO")
    print("=" * 80)
    print()

    for url in test_urls:
        print(f"URL: {url}")
        print("-" * 80)

        metadata = extractor.extract_from_url(url)

        print(f"  Country:   {metadata.get('country') or 'Not detected'}")
        print(f"  Region:    {metadata.get('region') or 'Not detected'}")
        print(f"  City:      {metadata.get('city') or 'Not detected'}")
        print(f"  Category:  {metadata.get('category') or 'Not detected'}")
        print(f"  Year:      {metadata.get('year') or 'Not detected'}")
        print(f"  Month:     {metadata.get('month') or 'Not detected'}")
        print()


def demo_country_normalization():
    """Demonstrate country name normalization."""
    from scraper.utils.metadata_extractor import COUNTRY_CODES

    test_countries = [
        "United States",
        "US",
        "usa",
        "United Kingdom",
        "UK",
        "France",
        "france",
    ]

    print("=" * 80)
    print("COUNTRY NORMALIZATION DEMO")
    print("=" * 80)
    print()

    for country in test_countries:
        country_lower = country.lower()
        normalized = COUNTRY_CODES.get(country_lower, country_lower)
        print(f"  {country:20} → {normalized:15}")
    print()


def demo_category_mapping():
    """Demonstrate category keyword mapping."""
    from scraper.utils.metadata_extractor import CATEGORY_KEYWORDS

    print("=" * 80)
    print("CATEGORY KEYWORD MAPPING")
    print("=" * 80)
    print()

    for category, keywords in CATEGORY_KEYWORDS.items():
        keywords_str = ", ".join(keywords[:5])  # Show first 5
        if len(keywords) > 5:
            keywords_str += f", ... (+{len(keywords) - 5} more)"
        print(f"  {category:15} → {keywords_str}")
    print()


def demo_statistics():
    """Show statistics about the extractor's knowledge base."""
    from scraper.utils.metadata_extractor import (
        COUNTRY_CODES,
        COUNTRIES_BY_REGION,
        CATEGORY_KEYWORDS,
    )

    print("=" * 80)
    print("METADATA EXTRACTOR STATISTICS")
    print("=" * 80)
    print()

    # Count stats
    print(f"  Total Countries: {len(COUNTRY_CODES)}")
    print(f"  Total Regions:   {len(COUNTRIES_BY_REGION)}")
    print(f"  Total Categories: {len(CATEGORY_KEYWORDS)}")
    print()

    # Show regions and country count
    print("  Countries by Region:")
    for region, countries in sorted(COUNTRIES_BY_REGION.items()):
        print(f"    {region:20} {len(countries):3} countries")
    print()


def demo_real_world_examples():
    """Demonstrate with real-world blog URL patterns."""
    extractor = MetadataExtractor()

    real_urls = [
        # Expat.com style
        "https://www.expat.com/en/guide/europe/france/12345-visa-requirements.html",
        # Blog with date
        "https://nomadlist.com/blog/2024/02/best-cities-digital-nomads/",
        # Simple slug
        "https://expatfocus.com/spain/living-barcelona-guide/",
        # Complex path
        "https://internations.org/magazine/life-abroad/thailand/bangkok-housing-market-2024",
    ]

    print("=" * 80)
    print("REAL-WORLD URL EXAMPLES")
    print("=" * 80)
    print()

    for url in real_urls:
        print(f"URL: {url}")
        print("-" * 80)

        metadata = extractor.extract_from_url(url)

        detected = []
        if metadata.get("country"):
            detected.append(f"Country: {metadata['country']}")
        if metadata.get("region"):
            detected.append(f"Region: {metadata['region']}")
        if metadata.get("city"):
            detected.append(f"City: {metadata['city']}")
        if metadata.get("category"):
            detected.append(f"Category: {metadata['category']}")
        if metadata.get("year"):
            detected.append(f"Year: {metadata['year']}")
        if metadata.get("month"):
            detected.append(f"Month: {metadata['month']}")

        if detected:
            print(f"  Detected: {', '.join(detected)}")
        else:
            print("  No metadata detected")
        print()


if __name__ == "__main__":
    """Run all demos."""
    demo_url_extraction()
    demo_country_normalization()
    demo_category_mapping()
    demo_statistics()
    demo_real_world_examples()

    print("=" * 80)
    print("DEMO COMPLETED")
    print("=" * 80)
    print()
    print("To use MetadataExtractor in your spider:")
    print()
    print("  from scraper.utils.metadata_extractor import MetadataExtractor")
    print()
    print("  extractor = MetadataExtractor()")
    print("  metadata = extractor.extract_all(url, response)")
    print()
    print("  # Access metadata:")
    print("  country = metadata.get('country')")
    print("  region = metadata.get('region')")
    print("  category = metadata.get('category')")
    print()
