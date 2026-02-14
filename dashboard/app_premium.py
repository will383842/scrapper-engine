"""
SCRAPER-PRO PREMIUM DASHBOARD
==============================

Ultra-professional Streamlit dashboard with:
- Beautiful UX with cards, metrics, animations
- Real-time deduplication statistics
- Visual indicators (progress bars, charts, badges)
- Tabs: "Scraping URLs" (active) + "Scraping Google" (coming soon)
- Configuration panel for future migration
- Professional color scheme and icons
"""

import csv
import hashlib
import hmac
import io
import json
import os
import time
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import requests
import streamlit as st
from sqlalchemy import create_engine, text

# ────────────────────────────────────────────────────────────
# PAGE CONFIG
# ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Scraper-Pro Premium",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────────────────────────────────────────────────
# CUSTOM CSS (PREMIUM DESIGN)
# ────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Main container */
    .main > div {
        padding-top: 2rem;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }

    .success-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .warning-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }

    .badge-active {
        background-color: #38ef7d;
        color: #0f3443;
    }

    .badge-disabled {
        background-color: #cbd5e0;
        color: #4a5568;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        font-weight: 600;
    }

    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* Headers */
    h1 {
        color: #1a202c;
        font-weight: 700;
    }

    h2, h3 {
        color: #2d3748;
    }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────
# DATABASE & API HELPERS
# ────────────────────────────────────────────────────────────

def get_db_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "scraper_db")
    user = os.getenv("POSTGRES_USER", "scraper_admin")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


@st.cache_resource
def get_engine():
    return create_engine(get_db_url(), pool_pre_ping=True)


def query_df(sql: str, params: dict | None = None):
    """Execute SQL and return list of dicts."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]


def query_scalar(sql: str, params: dict | None = None):
    """Execute SQL and return single scalar value."""
    engine = get_engine()
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar() or 0


SCRAPER_API_URL = os.getenv("SCRAPER_API_URL", "http://scraper:8000")
API_HMAC_SECRET = os.getenv("API_HMAC_SECRET", "")
SCRAPING_MODE = os.getenv("SCRAPING_MODE", "urls_only")


def api_request(method: str, path: str, json_data: dict | None = None) -> dict:
    """HMAC-signed request to scraper API."""
    url = f"{SCRAPER_API_URL}{path}"
    ts = str(int(time.time()))
    body_str = json.dumps(json_data) if json_data else ""

    sig = hmac.new(
        API_HMAC_SECRET.encode(), f"{ts}.{body_str}".encode(), hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Signature": sig,
        "X-Timestamp": ts,
        "Content-Type": "application/json",
    }

    resp = requests.request(method, url, headers=headers, json=json_data, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ────────────────────────────────────────────────────────────
# AUTHENTICATION
# ────────────────────────────────────────────────────────────

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🚀 Scraper-Pro Premium")
    st.markdown("### Dashboard Admin")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("Mot de passe", type="password", key="login_pw")
        if st.button("Connexion", type="primary", use_container_width=True):
            dashboard_pw = os.getenv("DASHBOARD_PASSWORD", "")
            if not dashboard_pw:
                st.error("❌ DASHBOARD_PASSWORD non configuré")
            elif hmac.compare_digest(password.encode(), dashboard_pw.encode()):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Mot de passe invalide")
    st.stop()

# ────────────────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────────────────

col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    st.title("🚀 Scraper-Pro Premium")
    st.markdown(f"**Mode:** `{SCRAPING_MODE.upper()}`")

with col_header2:
    if st.button("🔄 Rafraîchir", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

st.markdown("---")

# ────────────────────────────────────────────────────────────
# SIDEBAR (QUICK STATS)
# ────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("📊 Aperçu Rapide")

    try:
        # System health
        st.subheader("Santé Système")
        try:
            health = api_request("GET", "/health")
            if health.get("status") == "ok":
                st.success("✅ API Opérationnelle")
            else:
                st.warning("⚠️ API Dégradée")
        except Exception:
            st.error("❌ API Hors Ligne")

        # Quick metrics
        st.subheader("Métriques Clés")
        total_contacts = query_scalar("SELECT COUNT(*) FROM validated_contacts")
        st.metric("Contacts Totaux", f"{total_contacts:,}")

        total_jobs = query_scalar("SELECT COUNT(*) FROM scraping_jobs")
        st.metric("Jobs Totaux", f"{total_jobs:,}")

        running_jobs = query_scalar("SELECT COUNT(*) FROM scraping_jobs WHERE status = 'running'")
        if running_jobs > 0:
            st.metric("🟢 Jobs Actifs", running_jobs)
        else:
            st.info("Aucun job actif")

    except Exception as e:
        st.error(f"Erreur: {e}")

    st.markdown("---")
    st.caption("Scraper-Pro v2.0.0")
    st.caption("© 2025 Ultra-Professional")

# ────────────────────────────────────────────────────────────
# MAIN TABS
# ────────────────────────────────────────────────────────────

if SCRAPING_MODE == "urls_only":
    tab_urls, tab_google, tab_stats, tab_config = st.tabs([
        "📄 Scraping URLs (Actif)",
        "🔍 Scraping Google (Bientôt)",
        "📈 Statistiques",
        "⚙️ Configuration"
    ])
else:
    tab_urls, tab_google, tab_stats, tab_config = st.tabs([
        "📄 Scraping URLs",
        "🔍 Scraping Google",
        "📈 Statistiques",
        "⚙️ Configuration"
    ])

# ════════════════════════════════════════════════════════════
# TAB 1: SCRAPING URLs (ACTIF)
# ════════════════════════════════════════════════════════════

with tab_urls:
    st.header("📄 Scraping d'URLs Personnalisées")

    # MODE BADGE
    st.markdown(
        '<span class="badge badge-active">✅ MODE ACTIF</span>',
        unsafe_allow_html=True
    )
    st.markdown("Scraping direct d'URLs sans proxies. Parfait pour les sites connus.")

    st.markdown("---")

    # ──────────────────────────────────────────────────────
    # DEDUPLICATION STATISTICS (PREMIUM VISUAL)
    # ──────────────────────────────────────────────────────

    st.subheader("🔒 Déduplication Ultra-Professionnelle")

    try:
        # URL deduplication
        url_exact_count = query_scalar("""
            SELECT COUNT(*) FROM url_deduplication_cache WHERE dedup_type = 'exact'
        """)
        url_normalized_count = query_scalar("""
            SELECT COUNT(*) FROM url_deduplication_cache WHERE dedup_type = 'normalized'
        """)

        # Email deduplication
        email_count = query_scalar("SELECT COUNT(DISTINCT email) FROM scraped_contacts")

        # Content hash deduplication
        content_hash_count = query_scalar("SELECT COUNT(*) FROM content_hash_cache")

        # Display cards
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "🔗 URLs Exactes",
                f"{url_exact_count:,}",
                help="URLs dédupliquées (match exact)"
            )

        with col2:
            st.metric(
                "🌐 URLs Normalisées",
                f"{url_normalized_count:,}",
                help="URLs dédupliquées (http/https, www, etc.)"
            )

        with col3:
            st.metric(
                "📧 Emails Uniques",
                f"{email_count:,}",
                help="Emails dédupliqués globalement"
            )

        with col4:
            st.metric(
                "📄 Contenus Uniques",
                f"{content_hash_count:,}",
                help="Pages dédupliquées par hash de contenu"
            )

        # Deduplication rate
        total_scraped = query_scalar("SELECT COUNT(*) FROM scraped_contacts")
        if total_scraped > 0:
            dedup_rate = ((url_exact_count + url_normalized_count) / total_scraped) * 100
            st.progress(min(dedup_rate / 100, 1.0))
            st.caption(f"Taux de déduplication: {dedup_rate:.1f}% ({url_exact_count + url_normalized_count:,} URLs évitées sur {total_scraped:,} scrapes)")

    except Exception as e:
        st.warning(f"Impossible de charger les stats de déduplication: {e}")

    st.markdown("---")

    # ──────────────────────────────────────────────────────
    # JOBS LIST
    # ──────────────────────────────────────────────────────

    st.subheader("📋 Jobs de Scraping")

    try:
        jobs = query_df("""
            SELECT id, name, source_type, status, progress,
                   pages_scraped, contacts_extracted, errors_count,
                   created_at, started_at, completed_at
            FROM scraping_jobs
            WHERE source_type IN ('custom_urls', 'blog_content')
            ORDER BY created_at DESC
            LIMIT 50
        """)

        if jobs:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Jobs", len(jobs))
            col2.metric("🟢 Running", sum(1 for j in jobs if j["status"] == "running"))
            col3.metric("✅ Completed", sum(1 for j in jobs if j["status"] == "completed"))
            col4.metric("❌ Failed", sum(1 for j in jobs if j["status"] == "failed"))

            st.dataframe(
                jobs,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "progress": st.column_config.ProgressColumn("Progress", min_value=0, max_value=100),
                },
            )
        else:
            st.info("Aucun job de scraping d'URLs. Créez-en un ci-dessous.")
    except Exception as e:
        st.error(f"Erreur: {e}")

    st.markdown("---")

    # ──────────────────────────────────────────────────────
    # NEW JOB FORM (SIMPLIFIED FOR URLs ONLY)
    # ──────────────────────────────────────────────────────

    st.subheader("➕ Lancer un Nouveau Job")

    with st.form("new_job_urls"):
        job_name = st.text_input("Nom du job", value=f"Job URLs {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        source_type = st.selectbox(
            "Type de source",
            options=["custom_urls", "blog_content"],
            format_func=lambda x: "🔗 URLs Personnalisées" if x == "custom_urls" else "📝 Contenu Blog"
        )

        config = {}
        if source_type == "custom_urls":
            urls_text = st.text_area("URLs (une par ligne)", height=200, placeholder="https://example.com\nhttps://example2.com")
            config["urls"] = [u.strip() for u in urls_text.splitlines() if u.strip()]
        else:
            config["start_url"] = st.text_input("URL du blog", placeholder="https://www.example.com/blog/")
            config["max_articles"] = st.number_input("Max articles", min_value=10, max_value=1000, value=100)
            config["scrape_depth"] = st.number_input("Profondeur", min_value=1, max_value=5, value=2)

        col_cat, col_plat = st.columns(2)
        with col_cat:
            category = st.selectbox(
                "Catégorie",
                options=[None, "avocat", "assureur", "notaire", "medecin", "comptable", "traducteur"],
                format_func=lambda x: "Auto-detect" if x is None else x.capitalize()
            )
        with col_plat:
            platform = st.selectbox(
                "Plateforme",
                options=[None, "sos-expat", "ulixai"],
                format_func=lambda x: "Auto-detect" if x is None else x
            )

        auto_inject = st.checkbox("Injection automatique vers MailWizz", value=True)

        submitted = st.form_submit_button("🚀 Lancer le Job", type="primary", use_container_width=True)

    if submitted:
        if source_type == "custom_urls" and not config.get("urls"):
            st.error("❌ Vous devez fournir au moins une URL.")
        elif source_type == "blog_content" and not config.get("start_url"):
            st.error("❌ Vous devez fournir l'URL du blog.")
        else:
            try:
                result = api_request("POST", "/api/v1/scraping/jobs", {
                    "source_type": source_type,
                    "name": job_name,
                    "config": config,
                    "category": category,
                    "platform": platform,
                    "tags": [],
                    "auto_inject_mailwizz": auto_inject,
                })
                st.success(f"✅ Job créé! ID: {result['job_id']} - Status: {result['status']}")
                time.sleep(2)
                st.rerun()
            except requests.exceptions.HTTPError as e:
                st.error(f"❌ Erreur API: {e.response.text if e.response else e}")
            except Exception as e:
                st.error(f"❌ Erreur: {e}")

# ════════════════════════════════════════════════════════════
# TAB 2: SCRAPING GOOGLE (COMING SOON)
# ════════════════════════════════════════════════════════════

with tab_google:
    st.header("🔍 Scraping Google (Bientôt Disponible)")

    # MODE BADGE
    if SCRAPING_MODE == "urls_only":
        st.markdown(
            '<span class="badge badge-disabled">🔒 MODE DÉSACTIVÉ</span>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<span class="badge badge-active">✅ MODE ACTIF</span>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    if SCRAPING_MODE == "urls_only":
        st.info("""
        ### 🚀 Migration vers le Mode Complet

        Pour activer Google Search et Google Maps, vous devez:

        1. **Configurer un fournisseur de proxies**
           - Oxylabs, BrightData, ou SmartProxy
           - Coût: ~$500-2000/mois selon le volume

        2. **Ajouter une clé SerpAPI**
           - Pour le fallback anti-bot de Google
           - Coût: ~$50-200/mois (fallback seulement)

        3. **Mettre à jour la configuration**
           - Modifier `SCRAPING_MODE=full` dans `.env.production`
           - Ajouter `PROXY_PROVIDER`, `PROXY_USER`, `PROXY_PASS`
           - Ajouter `SERPAPI_KEY`

        4. **Redémarrer les services**
           ```bash
           docker-compose -f docker-compose.production.yml down
           docker-compose -f docker-compose.production.yml up -d
           ```

        Consultez le **Guide de Déploiement** pour plus de détails.
        """)
    else:
        st.success("✅ Mode complet activé! Vous pouvez maintenant scraper Google Search et Google Maps.")

        # Show Google scraping interface (similar to URLs tab)
        st.subheader("📋 Jobs Google")
        st.info("Interface Google complète ici (non implémentée dans cette version)")

# ════════════════════════════════════════════════════════════
# TAB 3: STATISTICS
# ════════════════════════════════════════════════════════════

with tab_stats:
    st.header("📈 Statistiques Détaillées")

    try:
        # Pipeline overview
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Contacts Scrapes", query_scalar("SELECT COUNT(*) FROM scraped_contacts"))
        col2.metric("Contacts Validés", query_scalar("SELECT COUNT(*) FROM validated_contacts"))
        col3.metric("Envoyés à MailWizz", query_scalar("SELECT COUNT(*) FROM validated_contacts WHERE status = 'sent_to_mailwizz'"))
        col4.metric("Bounced", query_scalar("SELECT COUNT(*) FROM validated_contacts WHERE status = 'bounced'"))

        st.markdown("---")

        # Deduplication breakdown
        st.subheader("🔒 Déduplication (Détails)")

        dedup_data = {
            "Type": ["URLs Exactes", "URLs Normalisées", "Emails", "Hash Contenu"],
            "Count": [
                query_scalar("SELECT COUNT(*) FROM url_deduplication_cache WHERE dedup_type = 'exact'"),
                query_scalar("SELECT COUNT(*) FROM url_deduplication_cache WHERE dedup_type = 'normalized'"),
                query_scalar("SELECT COUNT(DISTINCT email) FROM scraped_contacts"),
                query_scalar("SELECT COUNT(*) FROM content_hash_cache"),
            ]
        }

        import pandas as pd
        df_dedup = pd.DataFrame(dedup_data)
        st.bar_chart(df_dedup.set_index("Type"))

        st.markdown("---")

        # Contacts by platform
        st.subheader("📊 Contacts par Plateforme")
        by_platform = query_df("""
            SELECT platform, category, COUNT(*) as count
            FROM validated_contacts
            GROUP BY platform, category
            ORDER BY count DESC
        """)
        if by_platform:
            st.dataframe(by_platform, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur: {e}")

# ════════════════════════════════════════════════════════════
# TAB 4: CONFIGURATION
# ════════════════════════════════════════════════════════════

with tab_config:
    st.header("⚙️ Configuration Système")

    # System info
    st.subheader("🖥️ Informations Système")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Mode de Scraping**")
        st.code(SCRAPING_MODE.upper())

        st.markdown("**API URL**")
        st.code(SCRAPER_API_URL)

    with col2:
        st.markdown("**Base de Données**")
        st.code(f"{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'scraper_db')}")

        st.markdown("**Redis**")
        st.code(f"{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}")

    st.markdown("---")

    # Deduplication settings
    st.subheader("🔒 Paramètres de Déduplication")

    dedup_col1, dedup_col2 = st.columns(2)

    with dedup_col1:
        st.markdown("**TTL URLs (jours)**")
        st.code(os.getenv("DEDUP_URL_TTL_DAYS", "30"))

        st.markdown("**Email Global**")
        st.code(os.getenv("DEDUP_EMAIL_GLOBAL", "true"))

    with dedup_col2:
        st.markdown("**Hash Contenu Activé**")
        st.code(os.getenv("DEDUP_CONTENT_HASH_ENABLED", "true"))

        st.markdown("**Normalisation URL**")
        st.code(os.getenv("DEDUP_URL_NORMALIZE", "true"))

    st.markdown("---")

    # Health check
    st.subheader("🏥 Santé des Services")

    try:
        health = api_request("GET", "/health")
        health_col1, health_col2, health_col3 = st.columns(3)

        with health_col1:
            if health.get("status") == "ok":
                st.success("✅ API")
            else:
                st.error("❌ API")

        with health_col2:
            if health.get("postgres"):
                st.success("✅ PostgreSQL")
            else:
                st.error("❌ PostgreSQL")

        with health_col3:
            if health.get("redis"):
                st.success("✅ Redis")
            else:
                st.error("❌ Redis")

    except Exception:
        st.error("❌ Impossible de contacter l'API")

st.markdown("---")
st.caption("Scraper-Pro Premium v2.0.0 | Développé avec ❤️ par l'équipe Ultra-Professional")
