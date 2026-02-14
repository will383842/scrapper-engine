# Exemples d'utilisation - Article Filters Component

## 🎯 Cas d'usage réels

### Exemple 1 : Dashboard Simple

**Objectif** : Afficher un dashboard articles complet en 3 lignes de code.

```python
import streamlit as st
from dashboard.components import render_full_articles_dashboard
from sqlalchemy import create_engine

st.set_page_config(page_title="Articles Dashboard", layout="wide")

engine = create_engine("postgresql://user:pass@localhost:5432/scraper_db")
render_full_articles_dashboard(engine)
```

**Résultat:**
- ✅ Filtres dynamiques (langue, pays, région, catégorie, dates, recherche)
- ✅ Statistiques visuelles (graphiques Plotly)
- ✅ Tableau paginé des résultats
- ✅ Export CSV Excel-compatible

---

### Exemple 2 : Intégration dans Dashboard Existant

**Objectif** : Ajouter un onglet "Articles" à un dashboard multi-onglets.

```python
import streamlit as st
from dashboard.components import render_full_articles_dashboard
from sqlalchemy import create_engine

st.title("🚀 Scraper-Pro Dashboard")

# Créer les onglets
tab_jobs, tab_contacts, tab_articles, tab_stats = st.tabs([
    "📋 Jobs",
    "📧 Contacts",
    "📰 Articles",
    "📈 Statistiques"
])

# Onglet Articles
with tab_articles:
    engine = create_engine(get_db_url())  # votre fonction DB
    render_full_articles_dashboard(engine)

# Autres onglets...
with tab_jobs:
    st.header("Jobs de scraping")
    # ...
```

**Avantages:**
- 🔥 Zéro friction : 1 ligne de code
- 🎨 UX cohérente avec le reste du dashboard
- ⚡ Performance optimale avec cache

---

### Exemple 3 : Filtres Customisés + Export

**Objectif** : Utiliser les filtres de manière granulaire avec logique métier.

```python
import streamlit as st
from dashboard.components import (
    render_article_filters,
    get_filtered_articles,
    render_article_stats,
    export_filtered_articles
)
from sqlalchemy import create_engine

engine = create_engine(get_db_url())

st.header("📰 Articles - Vue Personnalisée")

# 1. Afficher les filtres
filters = render_article_filters(engine)

st.markdown("---")

# 2. Logique métier custom
total_articles = get_articles_count(engine, filters)

if total_articles == 0:
    st.warning("⚠️ Aucun article ne correspond aux critères.")
    st.stop()

if total_articles > 10000:
    st.info(f"💡 {total_articles:,} articles trouvés. Export limité à 10,000.")

# 3. Statistiques
st.subheader("📊 Vue d'ensemble")
render_article_stats(engine, filters)

st.markdown("---")

# 4. Résultats paginés
st.subheader("📋 Articles")
page_size = st.selectbox("Articles par page", [25, 50, 100], index=1)
page = st.number_input("Page", min_value=1, value=1, step=1)

offset = (page - 1) * page_size
articles = get_filtered_articles(engine, filters, limit=page_size, offset=offset)

if not articles.empty:
    st.dataframe(
        articles,
        use_container_width=True,
        column_config={
            "url": st.column_config.LinkColumn("URL"),
            "word_count": st.column_config.NumberColumn("Mots", format="%d"),
        }
    )
else:
    st.info("Aucun article à afficher.")

st.markdown("---")

# 5. Export
export_filtered_articles(engine, filters)
```

**Bénéfices:**
- 🎛️ Contrôle total sur le flow
- 📈 Statistiques séparées des résultats
- 💼 Logique métier intégrée
- 📥 Export flexible

---

### Exemple 4 : Multi-language Dashboard

**Objectif** : Dashboard avec traduction française/anglaise.

```python
import streamlit as st
from dashboard.components import render_article_filters, get_filtered_articles

# Sélecteur de langue
lang = st.sidebar.radio("Language / Langue", ["🇫🇷 Français", "🇬🇧 English"])
is_fr = "Français" in lang

# Titres traduits
st.title("📰 Articles" if is_fr else "📰 Articles Dashboard")

# Filtres
engine = create_engine(get_db_url())
filters = render_article_filters(engine)

# Message custom selon langue
total = get_articles_count(engine, filters)
if is_fr:
    st.success(f"✅ {total:,} articles trouvés")
else:
    st.success(f"✅ {total:,} articles found")

# Résultats
articles = get_filtered_articles(engine, filters, limit=50)
st.dataframe(articles)
```

---

### Exemple 5 : Export Programmable (sans UI)

**Objectif** : Exporter des articles via script sans Streamlit UI.

```python
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

def export_articles_to_csv(
    engine,
    output_path: str,
    language: str = None,
    country: str = None,
    date_from: str = None
):
    """
    Exporte des articles en CSV sans UI Streamlit.

    Args:
        engine: SQLAlchemy engine
        output_path: Chemin du fichier CSV
        language: Filtre langue (ex: "fr")
        country: Filtre pays (ex: "france")
        date_from: Date min ISO (ex: "2024-01-01")
    """
    query = """
        SELECT id, title, url, domain, language, country,
               word_count, date_published, excerpt
        FROM scraped_articles
        WHERE 1=1
    """
    params = {}

    if language:
        query += " AND language = :language"
        params["language"] = language

    if country:
        query += " AND country = :country"
        params["country"] = country

    if date_from:
        query += " AND date_published >= :date_from"
        params["date_from"] = date_from

    query += " ORDER BY date_published DESC"

    # Exécuter
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    # Sauvegarder avec BOM UTF-8
    with open(output_path, "w", encoding="utf-8-sig") as f:
        df.to_csv(f, index=False)

    print(f"✅ {len(df):,} articles exportés vers {output_path}")


# Usage
engine = create_engine("postgresql://user:pass@localhost:5432/scraper_db")
export_articles_to_csv(
    engine,
    output_path="articles_fr_2024.csv",
    language="fr",
    date_from="2024-01-01"
)
```

**Use cases:**
- 🤖 Exports automatisés (cron jobs)
- 📊 ETL pipelines
- 📧 Envoi par email programmé

---

### Exemple 6 : Recherche Avancée avec Highlights

**Objectif** : Mettre en surbrillance les mots recherchés dans les résultats.

```python
import streamlit as st
from dashboard.components import render_article_filters, get_filtered_articles

engine = create_engine(get_db_url())

# Filtres
filters = render_article_filters(engine)
search_term = filters.get("search", "")

# Résultats
articles = get_filtered_articles(engine, filters, limit=20)

if not articles.empty and search_term:
    st.subheader(f"🔍 Résultats pour: **{search_term}**")

    for _, article in articles.iterrows():
        # Highlight du terme dans le titre
        title = article["title"]
        if search_term.lower() in title.lower():
            title = title.replace(
                search_term,
                f"**:red[{search_term}]**"
            )

        # Affichage
        with st.expander(f"📄 {title}"):
            st.write(f"**Domaine:** {article['domain']}")
            st.write(f"**Mots:** {article['word_count']:,}")
            st.write(f"**Extrait:** {article['excerpt'][:200]}...")
            st.link_button("🔗 Lire l'article", article["url"])
else:
    st.dataframe(articles)
```

---

### Exemple 7 : Analytics Dashboard avec KPIs

**Objectif** : Dashboard analytique avec métriques clés.

```python
import streamlit as st
from dashboard.components import render_article_filters, get_articles_count
from sqlalchemy import create_engine, text

engine = create_engine(get_db_url())

st.title("📊 Articles Analytics Dashboard")

# Filtres
filters = render_article_filters(engine)

st.markdown("---")

# KPIs Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    total = get_articles_count(engine, filters)
    st.metric("📄 Total Articles", f"{total:,}")

with col2:
    # Moyenne mots
    query = """
        SELECT AVG(word_count) FROM scraped_articles
        WHERE language = :lang
    """
    with engine.connect() as conn:
        avg_words = conn.execute(
            text(query),
            {"lang": filters.get("language", "all")}
        ).scalar() or 0
    st.metric("📝 Mots Moyens", f"{int(avg_words):,}")

with col3:
    # Domaines uniques
    query = "SELECT COUNT(DISTINCT domain) FROM scraped_articles"
    with engine.connect() as conn:
        domains = conn.execute(text(query)).scalar()
    st.metric("🌐 Domaines", domains)

with col4:
    # Articles cette semaine
    query = """
        SELECT COUNT(*) FROM scraped_articles
        WHERE scraped_at > NOW() - INTERVAL '7 days'
    """
    with engine.connect() as conn:
        weekly = conn.execute(text(query)).scalar()
    st.metric("🆕 Cette Semaine", weekly)

st.markdown("---")

# Graphique tendance temporelle
st.subheader("📈 Tendance de Scraping")

query = """
    SELECT DATE(scraped_at) as date, COUNT(*) as count
    FROM scraped_articles
    WHERE scraped_at > NOW() - INTERVAL '30 days'
    GROUP BY DATE(scraped_at)
    ORDER BY date
"""

with engine.connect() as conn:
    df_trend = pd.read_sql(text(query), conn)

if not df_trend.empty:
    st.line_chart(df_trend.set_index("date"))
else:
    st.info("Pas de données pour les 30 derniers jours.")
```

---

## 🎓 Conseils d'utilisation

### ✅ Best Practices

1. **Cache Engine:** Créer l'engine une seule fois et le réutiliser
   ```python
   @st.cache_resource
   def get_engine():
       return create_engine(get_db_url())
   ```

2. **Pagination:** Limiter à 100-200 résultats max par page
   ```python
   articles = get_filtered_articles(engine, filters, limit=100)
   ```

3. **Performance:** Utiliser les index DB sur colonnes filtrées
   ```sql
   CREATE INDEX idx_articles_language ON scraped_articles(language);
   CREATE INDEX idx_articles_country ON scraped_articles(country);
   ```

4. **Error Handling:** Wrapper dans try/except pour robustesse
   ```python
   try:
       render_full_articles_dashboard(engine)
   except Exception as e:
       st.error(f"❌ Erreur: {e}")
   ```

### ❌ À éviter

1. **Ne pas recréer l'engine à chaque appel**
   ```python
   # ❌ MAUVAIS
   def render():
       engine = create_engine(...)  # recréé à chaque fois

   # ✅ BON
   engine = get_engine()  # cached
   ```

2. **Ne pas charger tous les articles sans limite**
   ```python
   # ❌ MAUVAIS : peut crasher si 100k articles
   articles = get_filtered_articles(engine, filters, limit=999999)

   # ✅ BON : pagination
   articles = get_filtered_articles(engine, filters, limit=50, offset=page*50)
   ```

3. **Ne pas oublier le BOM UTF-8 pour Excel**
   ```python
   # ❌ MAUVAIS : accents cassés dans Excel
   df.to_csv("export.csv", encoding="utf-8")

   # ✅ BON : BOM UTF-8
   with open("export.csv", "w", encoding="utf-8-sig") as f:
       df.to_csv(f, index=False)
   ```

---

## 🚀 Pour aller plus loin

Consultez:
- **README.md** : Documentation complète du composant
- **test_article_filters.py** : Tests unitaires et exemples
- **article_filters.py** : Code source commenté

---

**Happy Filtering! 📊🔍**
