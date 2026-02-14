"""
DEMO ARTICLE FILTERS - Application Standalone
==============================================

Démo rapide du composant article_filters sans le dashboard complet.

Usage:
    streamlit run dashboard/demo_article_filters.py

Fonctionnalités démontrées:
- Filtres dynamiques avec auto-populate
- Statistiques visuelles interactives
- Tableau des résultats paginés
- Export CSV Excel-compatible
"""

import os
import sys
from urllib.parse import quote_plus

import streamlit as st
from sqlalchemy import create_engine

# Ajouter le répertoire parent au path pour imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.components import render_full_articles_dashboard


# ════════════════════════════════════════════════════════════
# PAGE CONFIGURATION
# ════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Article Filters Demo",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════
# CSS STYLING
# ════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* ─── Main Layout ─── */
    .main > div {
        padding-top: 2rem;
    }

    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* ─── Headers ─── */
    h1 {
        color: #1a202c;
        font-weight: 800;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
    }

    h2, h3 {
        color: #2d3748;
        font-weight: 700;
    }

    /* ─── Buttons ─── */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }

    /* ─── Metrics ─── */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
    }

    /* ─── Dataframes ─── */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# DATABASE CONNECTION
# ════════════════════════════════════════════════════════════

@st.cache_resource
def get_engine():
    """Crée un engine SQLAlchemy (cached)."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "scraper_db")
    user = os.getenv("POSTGRES_USER", "scraper_admin")
    password = os.getenv("POSTGRES_PASSWORD", "")

    url = f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


# ════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════

col_header1, col_header2 = st.columns([3, 1])

with col_header1:
    st.title("📰 Article Filters - Démo Interactive")
    st.markdown("**Composant réutilisable pour explorer les articles scrapés**")

with col_header2:
    if st.button("🔄 Rafraîchir", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

st.markdown("---")

# ════════════════════════════════════════════════════════════
# SIDEBAR INFO
# ════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("ℹ️ À propos")

    st.markdown("""
    ### 🎯 Fonctionnalités

    ✅ **10 Filtres Dynamiques**
    - Langue, Pays, Région, Catégorie
    - Ville, Domaine, Dates
    - Recherche textuelle, Tri

    ✅ **Statistiques Visuelles**
    - Cartes métriques
    - Graphiques Plotly interactifs

    ✅ **Tableau Paginé**
    - Navigation fluide
    - Colonnes formatées

    ✅ **Export CSV**
    - Excel-compatible (UTF-8 BOM)
    - Jusqu'à 100k articles
    """)

    st.markdown("---")

    st.subheader("🔧 Configuration")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_name = os.getenv("POSTGRES_DB", "scraper_db")
    st.code(f"DB: {db_host}/{db_name}")

    st.markdown("---")

    st.subheader("📚 Documentation")
    st.markdown("""
    - [README.md](components/README.md)
    - [EXAMPLE.md](components/EXAMPLE.md)
    - [Livraison](ARTICLE_FILTERS_DELIVERY.md)
    """)

    st.markdown("---")
    st.caption("Article Filters v1.0")
    st.caption("© 2025 Scraper-Pro")

# ════════════════════════════════════════════════════════════
# MAIN CONTENT
# ════════════════════════════════════════════════════════════

try:
    # Tester la connexion DB
    engine = get_engine()
    with engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SELECT COUNT(*) FROM scraped_articles")).scalar()
        st.success(f"✅ Connexion DB réussie! {result:,} articles dans la base.")

    st.markdown("---")

    # Afficher le dashboard complet
    render_full_articles_dashboard(engine)

except ImportError as e:
    st.error("❌ Erreur d'import du composant")
    st.exception(e)
    st.info("💡 Assurez-vous que `dashboard/components/article_filters.py` existe.")

except Exception as e:
    st.error("❌ Erreur lors du chargement du dashboard")
    st.exception(e)

    # Debug info
    with st.expander("🐛 Informations de Debug", expanded=False):
        st.markdown("**Variables d'environnement:**")
        env_vars = {
            "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "NON DÉFINI"),
            "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "NON DÉFINI"),
            "POSTGRES_DB": os.getenv("POSTGRES_DB", "NON DÉFINI"),
            "POSTGRES_USER": os.getenv("POSTGRES_USER", "NON DÉFINI"),
            "POSTGRES_PASSWORD": "✅ Défini" if os.getenv("POSTGRES_PASSWORD") else "❌ NON DÉFINI",
        }
        st.json(env_vars)

# ════════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; opacity: 0.7;">
    <strong>Article Filters Component v1.0</strong><br>
    Démo Interactive - Scraper-Pro Dashboard<br>
    Made with ❤️ by Ultra-Professional Team
</div>
""", unsafe_allow_html=True)
