"""
Script de test pour le composant article_filters
=================================================

Test unitaire du composant article_filters hors Streamlit.

Usage:
    python dashboard/test_article_filters.py
"""

import os
import sys
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

# Ajouter le répertoire parent au path pour imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.components.article_filters import (
    get_unique_values,
    get_articles_count,
    _build_query_with_filters,
)


def get_test_engine():
    """Crée un engine de test depuis les variables d'environnement."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "scraper_db")
    user = os.getenv("POSTGRES_USER", "scraper_admin")
    password = os.getenv("POSTGRES_PASSWORD", "")

    url = f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"
    return create_engine(url, pool_pre_ping=True)


def test_get_unique_values():
    """Test de la fonction get_unique_values."""
    print("\n" + "="*60)
    print("TEST: get_unique_values")
    print("="*60)

    engine = get_test_engine()

    # Test 1: Langues
    print("\n1. Récupération des langues uniques...")
    try:
        languages = get_unique_values(engine, "language")
        print(f"✅ {len(languages)} langues trouvées: {languages[:5]}")
    except Exception as e:
        print(f"❌ Erreur: {e}")

    # Test 2: Pays
    print("\n2. Récupération des pays uniques...")
    try:
        countries = get_unique_values(engine, "country")
        print(f"✅ {len(countries)} pays trouvés: {countries[:5]}")
    except Exception as e:
        print(f"❌ Erreur: {e}")

    # Test 3: Catégories
    print("\n3. Récupération des catégories uniques...")
    try:
        categories = get_unique_values(engine, "category_expat")
        print(f"✅ {len(categories)} catégories trouvées: {categories}")
    except Exception as e:
        print(f"❌ Erreur: {e}")


def test_build_query():
    """Test de la construction de requêtes SQL."""
    print("\n" + "="*60)
    print("TEST: _build_query_with_filters")
    print("="*60)

    # Test 1: Requête sans filtres
    print("\n1. Requête sans filtres...")
    filters = {
        "language": "all",
        "country": "all",
        "region": "all",
        "category": "all",
        "search": "",
    }
    query, params = _build_query_with_filters(filters, count_only=True)
    print(f"✅ Query: {query[:100]}...")
    print(f"✅ Params: {params}")

    # Test 2: Requête avec filtres
    print("\n2. Requête avec filtres multiples...")
    filters = {
        "language": "fr",
        "country": "france",
        "region": "europe",
        "category": "guide",
        "search": "expatriation",
        "date_from": "2024-01-01",
    }
    query, params = _build_query_with_filters(filters, count_only=False, limit=10)
    print(f"✅ Query contient 'WHERE': {' WHERE ' in query}")
    print(f"✅ Params: {list(params.keys())}")
    print(f"✅ Limite appliquée: {'LIMIT' in query}")


def test_get_count():
    """Test du comptage d'articles."""
    print("\n" + "="*60)
    print("TEST: get_articles_count")
    print("="*60)

    engine = get_test_engine()

    # Test 1: Comptage total
    print("\n1. Comptage de tous les articles...")
    filters = {
        "language": "all",
        "country": "all",
        "region": "all",
        "category": "all",
        "search": "",
    }
    try:
        count = get_articles_count(engine, filters)
        print(f"✅ {count:,} articles totaux trouvés")
    except Exception as e:
        print(f"❌ Erreur: {e}")

    # Test 2: Comptage avec filtre langue
    print("\n2. Comptage articles français...")
    filters["language"] = "fr"
    try:
        count_fr = get_articles_count(engine, filters)
        print(f"✅ {count_fr:,} articles en français trouvés")
    except Exception as e:
        print(f"❌ Erreur: {e}")


def test_database_connection():
    """Test de la connexion à la base de données."""
    print("\n" + "="*60)
    print("TEST: Connexion Database")
    print("="*60)

    try:
        engine = get_test_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM scraped_articles")).scalar()
            print(f"✅ Connexion réussie!")
            print(f"✅ {result:,} articles dans la table scraped_articles")
            return True
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False


def main():
    """Exécute tous les tests."""
    print("\n" + "="*60)
    print("SCRAPER-PRO - Tests Article Filters Component")
    print("="*60)

    # Test 0: Connexion DB
    if not test_database_connection():
        print("\n❌ Impossible de continuer sans connexion DB")
        print("💡 Vérifiez vos variables d'environnement POSTGRES_*")
        return

    # Test 1: Valeurs uniques
    test_get_unique_values()

    # Test 2: Construction requêtes
    test_build_query()

    # Test 3: Comptage
    test_get_count()

    print("\n" + "="*60)
    print("✅ TOUS LES TESTS TERMINÉS")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
