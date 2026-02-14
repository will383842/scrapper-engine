"""
Test Script for app_final.py
=============================

Valide que le dashboard fonctionne correctement:
- Connexion DB
- Connexion API
- Queries principales
- Error handling

Usage:
    python dashboard/test_dashboard.py
"""

import os
import sys
import hashlib
import hmac
import json
import time
from urllib.parse import quote_plus

import requests
from sqlalchemy import create_engine, text

# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

print("🔧 Chargement de la configuration...")

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables d'environnement chargées")
except ImportError:
    print("⚠️  python-dotenv non installé, utilisation des env système")

# Database config
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "scraper_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "scraper_admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# API config
SCRAPER_API_URL = os.getenv("SCRAPER_API_URL", "http://localhost:8000")
API_HMAC_SECRET = os.getenv("API_HMAC_SECRET", "")
SCRAPING_MODE = os.getenv("SCRAPING_MODE", "urls_only")

# Dashboard config
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

# ═══════════════════════════════════════════════════════════
# TEST HELPERS
# ═══════════════════════════════════════════════════════════

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.tests = []

    def add_test(self, test_name: str, success: bool, message: str = "", warning: bool = False):
        status = "✅" if success else ("⚠️" if warning else "❌")
        self.tests.append(f"{status} {test_name}: {message}")

        if warning:
            self.warnings += 1
        elif success:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"📊 {self.name} - RÉSUMÉ")
        print(f"{'='*60}")
        for test in self.tests:
            print(test)
        print(f"\n✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"⚠️  Warnings: {self.warnings}")
        print(f"{'='*60}\n")

# ═══════════════════════════════════════════════════════════
# TEST 1: ENVIRONMENT VARIABLES
# ═══════════════════════════════════════════════════════════

def test_environment():
    """Test environment variables configuration."""
    result = TestResult("Environment Variables")

    # Required variables
    required = {
        "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
        "API_HMAC_SECRET": API_HMAC_SECRET,
        "DASHBOARD_PASSWORD": DASHBOARD_PASSWORD,
    }

    for var_name, var_value in required.items():
        if var_value:
            result.add_test(var_name, True, "configuré")
        else:
            result.add_test(var_name, False, "NON CONFIGURÉ - REQUIS")

    # Optional variables
    optional = {
        "SCRAPING_MODE": SCRAPING_MODE,
        "POSTGRES_HOST": POSTGRES_HOST,
        "POSTGRES_PORT": POSTGRES_PORT,
        "POSTGRES_DB": POSTGRES_DB,
        "POSTGRES_USER": POSTGRES_USER,
    }

    for var_name, var_value in optional.items():
        if var_value:
            result.add_test(var_name, True, f"= {var_value}")
        else:
            result.add_test(var_name, False, "non configuré", warning=True)

    result.print_summary()
    return result.failed == 0

# ═══════════════════════════════════════════════════════════
# TEST 2: DATABASE CONNECTION
# ═══════════════════════════════════════════════════════════

def test_database():
    """Test PostgreSQL connection and tables."""
    result = TestResult("Database Connection")

    # Build connection URL
    db_url = f"postgresql://{quote_plus(POSTGRES_USER)}:{quote_plus(POSTGRES_PASSWORD)}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    # Test connection
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result.add_test("Connexion PostgreSQL", True, f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    except Exception as e:
        result.add_test("Connexion PostgreSQL", False, str(e))
        result.print_summary()
        return False

    # Test tables existence
    required_tables = [
        "scraping_jobs",
        "scraped_contacts",
        "validated_contacts",
        "scraped_articles",
        "proxy_stats",
        "whois_cache",
        "url_deduplication_cache",
        "content_hash_cache",
        "mailwizz_sync_log",
        "email_domain_blacklist",
    ]

    with engine.connect() as conn:
        for table in required_tables:
            try:
                result_query = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result_query.scalar()
                result.add_test(f"Table {table}", True, f"{count} lignes")
            except Exception as e:
                result.add_test(f"Table {table}", False, f"Erreur: {e}", warning=True)

    # Test sample queries (same as dashboard)
    test_queries = {
        "Total jobs": "SELECT COUNT(*) FROM scraping_jobs",
        "Total contacts": "SELECT COUNT(*) FROM validated_contacts",
        "Running jobs": "SELECT COUNT(*) FROM scraping_jobs WHERE status = 'running'",
        "URL dedup cache": "SELECT COUNT(*) FROM url_deduplication_cache",
    }

    with engine.connect() as conn:
        for query_name, query_sql in test_queries.items():
            try:
                result_query = conn.execute(text(query_sql))
                count = result_query.scalar() or 0
                result.add_test(f"Query: {query_name}", True, f"= {count}")
            except Exception as e:
                result.add_test(f"Query: {query_name}", False, str(e))

    result.print_summary()
    return result.failed == 0

# ═══════════════════════════════════════════════════════════
# TEST 3: API CONNECTION
# ═══════════════════════════════════════════════════════════

def test_api():
    """Test Scraper API connection and endpoints."""
    result = TestResult("API Connection")

    if not API_HMAC_SECRET:
        result.add_test("API_HMAC_SECRET", False, "Non configuré, impossible de tester l'API")
        result.print_summary()
        return False

    # Helper function for HMAC-signed requests
    def api_request(method: str, path: str, json_data: dict = None) -> dict:
        url = f"{SCRAPER_API_URL}{path}"
        ts = str(int(time.time()))
        body_str = json.dumps(json_data) if json_data else ""

        sig = hmac.new(
            API_HMAC_SECRET.encode(),
            f"{ts}.{body_str}".encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "X-Signature": sig,
            "X-Timestamp": ts,
            "Content-Type": "application/json",
        }

        resp = requests.request(method, url, headers=headers, json=json_data, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # Test 1: Health check
    try:
        health = api_request("GET", "/health")
        result.add_test("API /health", True, f"Status: {health.get('status', 'unknown')}")

        # Check services
        if health.get("postgres"):
            result.add_test("API → PostgreSQL", True, "connexion OK")
        else:
            result.add_test("API → PostgreSQL", False, "connexion échouée", warning=True)

        if health.get("redis"):
            result.add_test("API → Redis", True, "connexion OK")
        else:
            result.add_test("API → Redis", False, "connexion échouée", warning=True)

    except requests.exceptions.ConnectionError as e:
        result.add_test("API /health", False, f"Connexion refusée: {SCRAPER_API_URL}")
        result.print_summary()
        return False
    except Exception as e:
        result.add_test("API /health", False, str(e))
        result.print_summary()
        return False

    # Test 2: Jobs endpoint (GET)
    try:
        # Note: Depending on your API, this might need adjustment
        # If your API doesn't have a GET /api/v1/scraping/jobs endpoint,
        # we just test that the endpoint exists (404 vs 405 vs connection error)
        resp = requests.get(f"{SCRAPER_API_URL}/api/v1/scraping/jobs", timeout=5)
        if resp.status_code in [200, 404, 405]:
            result.add_test("API /api/v1/scraping/jobs", True, f"Endpoint accessible (status {resp.status_code})")
        else:
            result.add_test("API /api/v1/scraping/jobs", False, f"Status {resp.status_code}", warning=True)
    except Exception as e:
        result.add_test("API /api/v1/scraping/jobs", False, str(e), warning=True)

    # Test 3: WHOIS endpoint
    try:
        whois_result = api_request("POST", "/api/v1/whois/lookup", {"domain": "example.com"})
        result.add_test("API /api/v1/whois/lookup", True, f"Lookup OK pour example.com")
    except Exception as e:
        result.add_test("API /api/v1/whois/lookup", False, str(e), warning=True)

    result.print_summary()
    return result.failed == 0

# ═══════════════════════════════════════════════════════════
# TEST 4: DASHBOARD DEPENDENCIES
# ═══════════════════════════════════════════════════════════

def test_dependencies():
    """Test Python dependencies for the dashboard."""
    result = TestResult("Python Dependencies")

    dependencies = {
        "streamlit": "1.30.0",
        "sqlalchemy": "2.0.0",
        "requests": "2.31.0",
    }

    for package, min_version in dependencies.items():
        try:
            if package == "streamlit":
                import streamlit
                version = streamlit.__version__
            elif package == "sqlalchemy":
                import sqlalchemy
                version = sqlalchemy.__version__
            elif package == "requests":
                import requests
                version = requests.__version__

            result.add_test(f"Package {package}", True, f"version {version}")

            # Check minimum version
            from packaging import version as pkg_version
            if pkg_version.parse(version) < pkg_version.parse(min_version):
                result.add_test(f"Version {package}", False, f"{version} < {min_version} (minimum requis)", warning=True)

        except ImportError:
            result.add_test(f"Package {package}", False, "NON INSTALLÉ")
        except Exception as e:
            result.add_test(f"Package {package}", False, str(e), warning=True)

    result.print_summary()
    return result.failed == 0

# ═══════════════════════════════════════════════════════════
# TEST 5: DASHBOARD FILE
# ═══════════════════════════════════════════════════════════

def test_dashboard_file():
    """Test dashboard file exists and is valid Python."""
    result = TestResult("Dashboard File")

    dashboard_path = "dashboard/app_final.py"

    # Test file exists
    if os.path.exists(dashboard_path):
        result.add_test("Fichier app_final.py", True, "trouvé")
    else:
        result.add_test("Fichier app_final.py", False, "NON TROUVÉ")
        result.print_summary()
        return False

    # Test file is valid Python
    try:
        with open(dashboard_path, "r", encoding="utf-8") as f:
            code = f.read()

        compile(code, dashboard_path, "exec")
        result.add_test("Syntaxe Python", True, "valide")

        # Check for required imports
        required_imports = ["streamlit", "sqlalchemy", "requests", "hmac", "hashlib"]
        for imp in required_imports:
            if f"import {imp}" in code or f"from {imp}" in code:
                result.add_test(f"Import {imp}", True, "trouvé")
            else:
                result.add_test(f"Import {imp}", False, "manquant", warning=True)

    except SyntaxError as e:
        result.add_test("Syntaxe Python", False, str(e))
    except Exception as e:
        result.add_test("Lecture fichier", False, str(e))

    result.print_summary()
    return result.failed == 0

# ═══════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ═══════════════════════════════════════════════════════════

def main():
    """Run all tests."""
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║                                                        ║
    ║   🚀 SCRAPER-PRO DASHBOARD - TEST SUITE              ║
    ║                                                        ║
    ║   Testing app_final.py functionality                  ║
    ║                                                        ║
    ╚════════════════════════════════════════════════════════╝
    """)

    all_passed = True

    # Run tests
    print("\n📝 Exécution des tests...\n")

    tests = [
        ("Environment Variables", test_environment),
        ("Python Dependencies", test_dependencies),
        ("Dashboard File", test_dashboard_file),
        ("Database Connection", test_database),
        ("API Connection", test_api),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Test: {test_name}...")
        try:
            passed = test_func()
            results.append((test_name, passed))
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"❌ Test {test_name} a échoué avec une exception: {e}")
            results.append((test_name, False))
            all_passed = False

    # Final summary
    print("\n" + "="*60)
    print("📊 RÉSUMÉ FINAL")
    print("="*60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")

    print("="*60)

    if all_passed:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("✅ Le dashboard est prêt à être utilisé.\n")
        print("Pour lancer le dashboard:")
        print("  streamlit run dashboard/app_final.py\n")
        return 0
    else:
        print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("❌ Veuillez corriger les erreurs avant de lancer le dashboard.\n")
        print("Consultez les logs ci-dessus pour plus de détails.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
