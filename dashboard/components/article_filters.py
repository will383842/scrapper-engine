"""
ARTICLE FILTERS COMPONENT - Composant réutilisable de filtres dynamiques
=============================================================================

Composant Streamlit ultra-premium pour filtrer et explorer les articles scrapés.

Fonctionnalités:
- Auto-populate depuis la base de données (valeurs uniques)
- Filtres multi-critères (langue, pays, région, catégorie, dates, recherche)
- Statistiques visuelles (graphiques Plotly)
- Export CSV avec BOM UTF-8 pour Excel
- Performance optimisée avec cache et pagination
- UX parfaite avec loading states et error handling

Usage:
    from dashboard.components.article_filters import render_article_filters, get_filtered_articles

    filters = render_article_filters(engine)
    articles = get_filtered_articles(engine, filters, limit=50)
"""

import csv
import io
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# ════════════════════════════════════════════════════════════
# HELPER FUNCTIONS - Database Queries
# ════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)  # Cache 5 minutes
def get_unique_values(_engine: Engine, column: str, order_by: str = None) -> List[str]:
    """
    Récupère les valeurs uniques d'une colonne.

    Args:
        _engine: SQLAlchemy engine (prefix _ pour éviter le cache)
        column: Nom de la colonne
        order_by: Ordre de tri (par défaut: alphabétique)

    Returns:
        Liste de valeurs uniques (sans None)
    """
    try:
        order_clause = order_by or column
        query = f"""
            SELECT DISTINCT {column}
            FROM scraped_articles
            WHERE {column} IS NOT NULL AND {column} != ''
            ORDER BY {order_clause}
        """

        with _engine.connect() as conn:
            result = conn.execute(text(query))
            return [row[0] for row in result]
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de {column}: {e}")
        return []


@st.cache_data(ttl=60)  # Cache 1 minute
def get_articles_count(_engine: Engine, filters: Dict[str, Any]) -> int:
    """
    Compte le nombre total d'articles correspondant aux filtres.

    Args:
        _engine: SQLAlchemy engine
        filters: Dictionnaire de filtres

    Returns:
        Nombre d'articles
    """
    try:
        query, params = _build_query_with_filters(filters, count_only=True)

        with _engine.connect() as conn:
            result = conn.execute(text(query), params).scalar()
            return int(result) if result else 0
    except Exception as e:
        st.error(f"❌ Erreur lors du comptage: {e}")
        return 0


def _build_query_with_filters(
    filters: Dict[str, Any],
    count_only: bool = False,
    limit: int = 50,
    offset: int = 0
) -> tuple[str, Dict[str, Any]]:
    """
    Construit la requête SQL avec tous les filtres appliqués.

    Args:
        filters: Dictionnaire de filtres
        count_only: Si True, retourne COUNT(*) au lieu des colonnes
        limit: Nombre max de résultats
        offset: Offset pour pagination

    Returns:
        Tuple (query_string, params_dict)
    """
    params = {}

    if count_only:
        query = "SELECT COUNT(*) FROM scraped_articles WHERE 1=1"
    else:
        query = """
            SELECT
                id, title, url, domain, language, country, region, city,
                category_expat, word_count, author, date_published,
                scraped_at, excerpt, tags, categories
            FROM scraped_articles
            WHERE 1=1
        """

    # Filtre langue
    if filters.get("language") and filters["language"] != "all":
        query += " AND language = :language"
        params["language"] = filters["language"]

    # Filtre pays
    if filters.get("country") and filters["country"] != "all":
        query += " AND country = :country"
        params["country"] = filters["country"]

    # Filtre région
    if filters.get("region") and filters["region"] != "all":
        query += " AND region = :region"
        params["region"] = filters["region"]

    # Filtre catégorie
    if filters.get("category") and filters["category"] != "all":
        query += " AND category_expat = :category"
        params["category"] = filters["category"]

    # Filtre ville
    if filters.get("city") and filters["city"] != "all":
        query += " AND city = :city"
        params["city"] = filters["city"]

    # Filtre domaine
    if filters.get("domain") and filters["domain"] != "all":
        query += " AND domain = :domain"
        params["domain"] = filters["domain"]

    # Filtre date minimum
    if filters.get("date_from"):
        query += " AND date_published >= :date_from"
        params["date_from"] = filters["date_from"]

    # Filtre date maximum
    if filters.get("date_to"):
        query += " AND date_published <= :date_to"
        params["date_to"] = filters["date_to"]

    # Recherche textuelle
    if filters.get("search") and filters["search"].strip():
        query += " AND (title ILIKE :search OR content_text ILIKE :search OR excerpt ILIKE :search)"
        params["search"] = f"%{filters['search'].strip()}%"

    # Tri et pagination (sauf pour COUNT)
    if not count_only:
        sort_map = {
            "date_published DESC": "date_published DESC NULLS LAST",
            "scraped_at DESC": "scraped_at DESC",
            "word_count DESC": "word_count DESC NULLS LAST",
            "title ASC": "title ASC",
            "country ASC": "country ASC NULLS LAST",
        }
        sort_clause = sort_map.get(filters.get("sort_by", "date_published DESC"), "date_published DESC NULLS LAST")

        query += f" ORDER BY {sort_clause}"
        query += " LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

    return query, params


# ════════════════════════════════════════════════════════════
# MAIN FILTER COMPONENT
# ════════════════════════════════════════════════════════════

def render_article_filters(engine: Engine) -> Dict[str, Any]:
    """
    Affiche l'interface de filtres pour les articles et retourne les valeurs sélectionnées.

    Args:
        engine: SQLAlchemy engine pour les requêtes

    Returns:
        Dictionnaire contenant tous les filtres sélectionnés:
        {
            "language": str | "all",
            "country": str | "all",
            "region": str | "all",
            "category": str | "all",
            "city": str | "all",
            "domain": str | "all",
            "date_from": date | None,
            "date_to": date | None,
            "search": str,
            "sort_by": str,
        }
    """

    st.markdown("### 🔍 Filtres de Recherche")
    st.markdown("---")

    # ─── Charger les valeurs uniques depuis la DB ───
    with st.spinner("⏳ Chargement des filtres..."):
        languages = get_unique_values(engine, "language")
        countries = get_unique_values(engine, "country")
        regions = get_unique_values(engine, "region")
        categories = get_unique_values(engine, "category_expat")
        cities = get_unique_values(engine, "city")
        domains = get_unique_values(engine, "domain")

    # ─── Filtres principaux (4 colonnes) ───
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        language = st.selectbox(
            "🌐 Langue",
            options=["all"] + languages,
            format_func=lambda x: "🌍 Toutes les langues" if x == "all" else f"🗣️ {x.upper()}",
            key="filter_language",
            help="Filtrer par langue de l'article"
        )

    with col2:
        country = st.selectbox(
            "🌍 Pays",
            options=["all"] + countries,
            format_func=lambda x: "🌎 Tous les pays" if x == "all" else f"📍 {x.title()}",
            key="filter_country",
            help="Filtrer par pays"
        )

    with col3:
        region = st.selectbox(
            "🗺️ Région",
            options=["all"] + regions,
            format_func=lambda x: "🌐 Toutes les régions" if x == "all" else f"🗺️ {x.title()}",
            key="filter_region",
            help="Filtrer par région géographique"
        )

    with col4:
        category = st.selectbox(
            "📂 Catégorie",
            options=["all"] + categories,
            format_func=lambda x: "📚 Toutes les catégories" if x == "all" else f"📂 {x.title()}",
            key="filter_category",
            help="Filtrer par catégorie Expat.com"
        )

    # ─── Filtres secondaires (3 colonnes + bouton reset) ───
    col5, col6, col7, col8 = st.columns([2, 2, 2, 1])

    with col5:
        city = st.selectbox(
            "🏙️ Ville",
            options=["all"] + cities,
            format_func=lambda x: "🌆 Toutes les villes" if x == "all" else f"🏙️ {x.title()}",
            key="filter_city",
            help="Filtrer par ville"
        )

    with col6:
        domain = st.selectbox(
            "🌐 Domaine",
            options=["all"] + domains,
            format_func=lambda x: "🌐 Tous les domaines" if x == "all" else f"🔗 {x}",
            key="filter_domain",
            help="Filtrer par nom de domaine"
        )

    with col7:
        sort_by = st.selectbox(
            "🔄 Trier par",
            options=[
                "date_published DESC",
                "scraped_at DESC",
                "word_count DESC",
                "title ASC",
                "country ASC",
            ],
            format_func=lambda x: {
                "date_published DESC": "📅 Date publication (↓)",
                "scraped_at DESC": "🕒 Date scraping (↓)",
                "word_count DESC": "📝 Nb mots (↓)",
                "title ASC": "🔤 Titre (A→Z)",
                "country ASC": "🌍 Pays (A→Z)",
            }.get(x, x),
            key="filter_sort",
            help="Ordre de tri des résultats"
        )

    with col8:
        st.write("")  # Spacer pour alignement
        # UX IMPROVEMENT 5: Better feedback for reset filters
        if st.button("🔄 Reset", use_container_width=True, help="Réinitialiser tous les filtres"):
            # Clear session state
            for key in list(st.session_state.keys()):
                if key.startswith("filter_"):
                    del st.session_state[key]
            st.success("✅ Filtres réinitialisés")
            time.sleep(1.5)
            st.rerun()

    # ─── Filtres de dates (2 colonnes) ───
    col9, col10 = st.columns(2)

    with col9:
        date_from = st.date_input(
            "📅 Date de publication (min)",
            value=None,
            key="filter_date_from",
            help="Articles publiés après cette date"
        )

    with col10:
        date_to = st.date_input(
            "📅 Date de publication (max)",
            value=None,
            key="filter_date_to",
            help="Articles publiés avant cette date"
        )

    # ─── Recherche textuelle ───
    search = st.text_input(
        "🔎 Recherche dans titre, contenu et extrait",
        placeholder="Entrez des mots-clés...",
        key="filter_search",
        help="Recherche insensible à la casse"
    )

    st.markdown("---")

    # ─── Compteur de résultats ───
    filters = {
        "language": language,
        "country": country,
        "region": region,
        "category": category,
        "city": city,
        "domain": domain,
        "date_from": date_from,
        "date_to": date_to,
        "search": search,
        "sort_by": sort_by,
    }

    total_results = get_articles_count(engine, filters)

    if total_results > 0:
        st.markdown(f"<div style='text-align:center;'><h3>📊 <strong>{total_results:,}</strong> articles trouvés</h3></div>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Aucun article ne correspond aux filtres sélectionnés.")

    return filters


# ════════════════════════════════════════════════════════════
# ARTICLE DATA FETCHING
# ════════════════════════════════════════════════════════════

def get_filtered_articles(
    engine: Engine,
    filters: Dict[str, Any],
    limit: int = 50,
    offset: int = 0
) -> pd.DataFrame:
    """
    Récupère les articles filtrés sous forme de DataFrame.

    Args:
        engine: SQLAlchemy engine
        filters: Dictionnaire de filtres (retourné par render_article_filters)
        limit: Nombre max d'articles à retourner
        offset: Offset pour pagination

    Returns:
        DataFrame Pandas avec les articles
    """
    try:
        query, params = _build_query_with_filters(filters, count_only=False, limit=limit, offset=offset)

        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)

            # Formater les dates pour affichage
            if "date_published" in df.columns:
                df["date_published"] = pd.to_datetime(df["date_published"], errors="coerce")
            if "scraped_at" in df.columns:
                df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")

            return df
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des articles: {e}")
        return pd.DataFrame()


# ════════════════════════════════════════════════════════════
# STATISTICS & VISUALIZATIONS
# ════════════════════════════════════════════════════════════

def render_article_stats(engine: Engine, filters: Dict[str, Any]):
    """
    Affiche des statistiques visuelles sur les articles filtrés.

    Args:
        engine: SQLAlchemy engine
        filters: Filtres actifs
    """

    st.markdown("### 📊 Statistiques Visuelles")
    st.markdown("---")

    try:
        # ─── Metrics Cards ───
        col1, col2, col3, col4 = st.columns(4)

        # Total articles
        with col1:
            total = get_articles_count(engine, filters)
            st.metric("📄 Total Articles", f"{total:,}")

        # Langues uniques
        with col2:
            query, params = _build_query_with_filters(filters, count_only=False)
            query_distinct = query.replace("SELECT id, title", "SELECT DISTINCT language", 1).split("ORDER BY")[0]
            with engine.connect() as conn:
                lang_count = conn.execute(text(query_distinct), params).rowcount
            st.metric("🌐 Langues", lang_count)

        # Pays uniques
        with col3:
            query_countries = query.replace("SELECT id, title", "SELECT DISTINCT country", 1).split("ORDER BY")[0]
            with engine.connect() as conn:
                country_count = conn.execute(text(query_countries), params).rowcount
            st.metric("🌍 Pays", country_count)

        # Mots moyens
        with col4:
            query_avg = query.replace("SELECT id, title", "SELECT AVG(word_count)", 1).split("ORDER BY")[0]
            with engine.connect() as conn:
                avg_words = conn.execute(text(query_avg), params).scalar()
                avg_words = int(avg_words) if avg_words else 0
            st.metric("📝 Mots Moyen", f"{avg_words:,}")

        st.markdown("---")

        # ─── Graphiques avec Plotly ───
        if PLOTLY_AVAILABLE and total > 0:
            col1, col2 = st.columns(2)

            # Graph 1: Distribution par langue
            with col1:
                st.subheader("🗣️ Répartition par Langue")
                query_lang = """
                    SELECT language, COUNT(*) as count
                    FROM scraped_articles
                    WHERE 1=1
                """
                # Ajouter les filtres (sauf langue)
                temp_filters = filters.copy()
                temp_filters["language"] = "all"
                _, params_lang = _build_query_with_filters(temp_filters)

                # Rebuild query with filters
                for key, value in params_lang.items():
                    if key not in ["limit", "offset"] and value and value != "all":
                        query_lang += f" AND {key} = :{key}"

                query_lang += " GROUP BY language ORDER BY count DESC LIMIT 10"

                with engine.connect() as conn:
                    lang_data = pd.read_sql(text(query_lang), conn, params={k:v for k,v in params_lang.items() if k not in ["limit", "offset"]})

                if not lang_data.empty:
                    fig = px.pie(
                        lang_data,
                        values="count",
                        names="language",
                        title="Distribution des langues",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Pas assez de données pour le graphique")

            # Graph 2: Distribution par pays
            with col2:
                st.subheader("🌍 Répartition par Pays")
                query_country = """
                    SELECT country, COUNT(*) as count
                    FROM scraped_articles
                    WHERE country IS NOT NULL
                """
                temp_filters = filters.copy()
                temp_filters["country"] = "all"
                _, params_country = _build_query_with_filters(temp_filters)

                for key, value in params_country.items():
                    if key not in ["limit", "offset"] and value and value != "all":
                        query_country += f" AND {key} = :{key}"

                query_country += " GROUP BY country ORDER BY count DESC LIMIT 10"

                with engine.connect() as conn:
                    country_data = pd.read_sql(text(query_country), conn, params={k:v for k,v in params_country.items() if k not in ["limit", "offset"]})

                if not country_data.empty:
                    fig = px.bar(
                        country_data,
                        x="country",
                        y="count",
                        title="Top 10 pays",
                        color="count",
                        color_continuous_scale="Blues"
                    )
                    fig.update_layout(showlegend=False, xaxis_title="Pays", yaxis_title="Nombre d'articles")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Pas assez de données pour le graphique")

        elif not PLOTLY_AVAILABLE:
            st.info("📊 Installez `plotly` pour voir les graphiques interactifs: `pip install plotly`")

    except Exception as e:
        st.error(f"❌ Erreur lors du calcul des statistiques: {e}")


# ════════════════════════════════════════════════════════════
# CSV EXPORT
# ════════════════════════════════════════════════════════════

def export_filtered_articles(engine: Engine, filters: Dict[str, Any]):
    """
    Exporte les articles filtrés en CSV avec support Excel (UTF-8 BOM).

    Args:
        engine: SQLAlchemy engine
        filters: Filtres actifs
    """

    st.markdown("### 📥 Export CSV")
    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.info("💡 **Export Excel-compatible** : UTF-8 avec BOM pour affichage parfait dans Excel")

    with col2:
        if st.button("📥 Exporter CSV", type="primary", use_container_width=True):
            with st.spinner("⏳ Génération du CSV..."):
                try:
                    # Fetch all articles (pas de limite)
                    df = get_filtered_articles(engine, filters, limit=100000, offset=0)

                    if df.empty:
                        st.warning("⚠️ Aucun article à exporter.")
                        return

                    # Préparer les colonnes pour export
                    export_columns = [
                        "id", "title", "url", "domain", "language",
                        "country", "region", "city", "category_expat",
                        "word_count", "author", "date_published", "excerpt"
                    ]

                    # Filtrer les colonnes existantes
                    export_columns = [col for col in export_columns if col in df.columns]
                    df_export = df[export_columns].copy()

                    # Formater les dates
                    for col in ["date_published", "scraped_at"]:
                        if col in df_export.columns:
                            df_export[col] = df_export[col].dt.strftime("%Y-%m-%d %H:%M:%S")

                    # Convertir en CSV avec BOM UTF-8 (pour Excel)
                    buffer = io.StringIO()
                    buffer.write("\ufeff")  # BOM UTF-8
                    df_export.to_csv(buffer, index=False, encoding="utf-8")
                    csv_data = buffer.getvalue()

                    # Timestamp pour nom de fichier
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"articles_filtered_{timestamp}.csv"

                    st.download_button(
                        label=f"⬇️ Télécharger CSV ({len(df_export):,} articles)",
                        data=csv_data.encode("utf-8"),
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True,
                    )

                    st.success(f"✅ {len(df_export):,} articles exportés avec succès!")

                except Exception as e:
                    st.error(f"❌ Erreur lors de l'export: {e}")


# ════════════════════════════════════════════════════════════
# FULL DASHBOARD DISPLAY
# ════════════════════════════════════════════════════════════

def render_full_articles_dashboard(engine: Engine):
    """
    Affiche le dashboard complet des articles avec filtres, stats et export.

    Cette fonction combine tous les composants pour un dashboard clé-en-main.

    Args:
        engine: SQLAlchemy engine
    """

    st.header("📰 Articles Scrapés - Dashboard Complet")
    st.markdown("---")

    # 1. Filtres
    filters = render_article_filters(engine)

    st.markdown("---")

    # 2. Statistiques
    render_article_stats(engine, filters)

    st.markdown("---")

    # 3. Tableau des résultats
    st.subheader("📋 Résultats")

    try:
        # Pagination
        col_p1, col_p2, col_p3 = st.columns([1, 2, 1])

        with col_p1:
            page_size = st.selectbox("Articles par page", options=[10, 25, 50, 100], index=2)

        with col_p2:
            total_articles = get_articles_count(engine, filters)
            total_pages = max(1, (total_articles + page_size - 1) // page_size)
            page = st.number_input(
                f"Page (1-{total_pages})",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1
            )

        with col_p3:
            st.metric("Total Pages", total_pages)

        # Fetch articles
        offset = (page - 1) * page_size
        df = get_filtered_articles(engine, filters, limit=page_size, offset=offset)

        if not df.empty:
            # Display dataframe avec configuration
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "url": st.column_config.LinkColumn("URL", width="medium"),
                    "word_count": st.column_config.NumberColumn("Mots", format="%d"),
                    "date_published": st.column_config.DatetimeColumn("Publié", format="DD/MM/YYYY HH:mm"),
                    "scraped_at": st.column_config.DatetimeColumn("Scrapé", format="DD/MM/YYYY HH:mm"),
                },
                hide_index=True,
            )

            st.caption(f"Affichage de {offset + 1} à {min(offset + page_size, total_articles)} sur {total_articles:,} articles")
        else:
            st.warning("⚠️ Aucun article à afficher.")

    except Exception as e:
        st.error(f"❌ Erreur lors de l'affichage: {e}")

    st.markdown("---")

    # 4. Export
    export_filtered_articles(engine, filters)
