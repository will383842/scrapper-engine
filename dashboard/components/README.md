# Dashboard Components - Scraper-Pro

## 📦 Vue d'ensemble

Ce package contient des composants réutilisables pour le dashboard Scraper-Pro, conçus pour être modulaires, performants et faciles à intégrer.

## 🎯 Composants disponibles

### 1. Article Filters (`article_filters.py`)

Composant ultra-premium de filtres dynamiques pour explorer les articles scrapés.

#### ✨ Fonctionnalités

- **Filtres auto-populate** : Chargement automatique des valeurs uniques depuis la DB
- **Multi-critères** : Langue, pays, région, catégorie, ville, domaine, dates, recherche textuelle
- **Statistiques visuelles** : Graphiques Plotly interactifs (pie charts, bar charts)
- **Export CSV** : Compatible Excel avec UTF-8 BOM
- **Performance** : Cache Streamlit (5min pour filtres, 1min pour comptage)
- **Pagination** : Navigation fluide avec pages personnalisables
- **UX Premium** : Loading states, error handling, formatage des nombres

#### 📖 Usage de base

```python
from dashboard.components import render_article_filters, get_filtered_articles
from sqlalchemy import create_engine

# 1. Créer un engine SQLAlchemy
engine = create_engine("postgresql://user:pass@localhost:5432/scraper_db")

# 2. Afficher les filtres (retourne un dict de valeurs)
filters = render_article_filters(engine)

# 3. Récupérer les articles filtrés
articles_df = get_filtered_articles(engine, filters, limit=50, offset=0)

# 4. Utiliser le DataFrame
st.dataframe(articles_df)
```

#### 🚀 Usage avancé (Dashboard complet)

```python
from dashboard.components import render_full_articles_dashboard
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:pass@localhost:5432/scraper_db")

# Affiche tout: filtres + stats + tableau + export
render_full_articles_dashboard(engine)
```

#### 📊 Filtres retournés

La fonction `render_article_filters()` retourne un dictionnaire:

```python
{
    "language": "fr" | "all",
    "country": "france" | "all",
    "region": "europe" | "all",
    "category": "guide" | "all",
    "city": "paris" | "all",
    "domain": "example.com" | "all",
    "date_from": date(2024, 1, 1) | None,
    "date_to": date(2024, 12, 31) | None,
    "search": "mot-clé" | "",
    "sort_by": "date_published DESC" | "word_count DESC" | ...,
}
```

#### 🎨 Fonctions disponibles

##### 1. `render_article_filters(engine: Engine) -> Dict[str, Any]`

Affiche l'interface de filtres et retourne les valeurs sélectionnées.

**Paramètres:**
- `engine`: SQLAlchemy Engine connecté à la DB

**Retour:**
- Dictionnaire de filtres

**Exemple:**
```python
filters = render_article_filters(engine)
# User interacts with UI, filters are updated
```

---

##### 2. `get_filtered_articles(engine, filters, limit=50, offset=0) -> pd.DataFrame`

Récupère les articles filtrés sous forme de DataFrame Pandas.

**Paramètres:**
- `engine`: SQLAlchemy Engine
- `filters`: Dict retourné par `render_article_filters()`
- `limit`: Nombre max d'articles (défaut: 50)
- `offset`: Offset pour pagination (défaut: 0)

**Retour:**
- DataFrame Pandas avec colonnes:
  - `id`, `title`, `url`, `domain`, `language`, `country`, `region`, `city`
  - `category_expat`, `word_count`, `author`, `date_published`, `scraped_at`
  - `excerpt`, `tags`, `categories`

**Exemple:**
```python
# Page 1 (0-49)
articles = get_filtered_articles(engine, filters, limit=50, offset=0)

# Page 2 (50-99)
articles = get_filtered_articles(engine, filters, limit=50, offset=50)
```

---

##### 3. `render_article_stats(engine: Engine, filters: Dict[str, Any])`

Affiche des statistiques visuelles sur les articles filtrés.

**Fonctionnalités:**
- Cartes métriques : Total, langues uniques, pays uniques, mots moyens
- Graphiques Plotly : Distribution par langue (pie), distribution par pays (bar)

**Exemple:**
```python
filters = render_article_filters(engine)
render_article_stats(engine, filters)
```

---

##### 4. `export_filtered_articles(engine: Engine, filters: Dict[str, Any])`

Affiche un bouton d'export CSV avec support Excel (UTF-8 BOM).

**Fonctionnalités:**
- Export jusqu'à 100,000 articles
- UTF-8 avec BOM pour compatibilité Excel
- Nom de fichier avec timestamp
- Formatage des dates lisibles

**Exemple:**
```python
filters = render_article_filters(engine)
export_filtered_articles(engine, filters)
# User clicks button → CSV download
```

---

##### 5. `render_full_articles_dashboard(engine: Engine)`

Dashboard complet clé-en-main combinant tous les composants.

**Inclut:**
1. Filtres dynamiques
2. Statistiques visuelles
3. Tableau paginé des résultats
4. Export CSV

**Exemple:**
```python
render_full_articles_dashboard(engine)
# Everything is rendered automatically
```

---

#### 🗄️ Schéma de la table `scraped_articles`

Le composant s'attend à une table PostgreSQL avec cette structure:

```sql
CREATE TABLE scraped_articles (
    id SERIAL PRIMARY KEY,
    job_id INTEGER,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    content_text TEXT,
    content_html TEXT,
    excerpt TEXT,
    author TEXT,
    date_published TIMESTAMPTZ,
    categories TEXT[],
    tags TEXT[],
    external_links JSONB,
    internal_links JSONB,
    featured_image_url TEXT,
    meta_description TEXT,
    word_count INTEGER,
    language VARCHAR(10),
    domain TEXT,
    country VARCHAR(100),      -- Migration 005
    region VARCHAR(100),       -- Migration 005
    city VARCHAR(100),         -- Migration 005
    category_expat VARCHAR(100), -- Migration 005
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index recommandés
CREATE INDEX idx_articles_language ON scraped_articles(language);
CREATE INDEX idx_articles_country ON scraped_articles(country);
CREATE INDEX idx_articles_region ON scraped_articles(region);
CREATE INDEX idx_articles_category_expat ON scraped_articles(category_expat);
CREATE INDEX idx_articles_date_published ON scraped_articles(date_published DESC);
```

#### ⚙️ Performance & Optimisation

**Cache Streamlit:**
- Valeurs uniques (filtres) : **5 minutes**
- Comptage articles : **1 minute**
- Requêtes optimisées avec index DB

**Recommandations:**
- Créer des index sur `language`, `country`, `region`, `category_expat`, `date_published`
- Limiter les résultats à 100-200 par page max
- Utiliser la pagination pour grands volumes

**Queries SQL:**
- Utilise des paramètres bindés (protection SQL injection)
- Pagination avec `LIMIT` et `OFFSET`
- Tri personnalisable (date, mots, titre, pays)

#### 🎨 Dépendances

**Required:**
- `streamlit >= 1.30.0`
- `sqlalchemy >= 2.0.0`
- `pandas >= 2.1.0`
- `psycopg2-binary >= 2.9.9`

**Optional (pour graphiques):**
- `plotly >= 5.18.0` (recommandé pour statistiques visuelles)

Si Plotly n'est pas installé, les statistiques fonctionnent sans graphiques.

#### 📝 Exemples d'intégration

##### Exemple 1 : Intégration dans un onglet Streamlit

```python
import streamlit as st
from dashboard.components import render_full_articles_dashboard
from sqlalchemy import create_engine

# Dans votre dashboard principal
tab1, tab2, tab3 = st.tabs(["Jobs", "Contacts", "Articles"])

with tab3:
    st.header("📰 Articles Scrapés")
    engine = create_engine(get_db_url())
    render_full_articles_dashboard(engine)
```

##### Exemple 2 : Filtres séparés des résultats

```python
import streamlit as st
from dashboard.components import (
    render_article_filters,
    get_filtered_articles,
    export_filtered_articles
)
from sqlalchemy import create_engine

engine = create_engine(get_db_url())

# Section filtres
with st.expander("🔍 Filtres", expanded=True):
    filters = render_article_filters(engine)

# Section résultats
st.subheader("📋 Résultats")
articles = get_filtered_articles(engine, filters, limit=50)
st.dataframe(articles)

# Section export
export_filtered_articles(engine, filters)
```

##### Exemple 3 : Customisation avancée

```python
from dashboard.components import render_article_filters, get_filtered_articles

engine = create_engine(get_db_url())

# Filtres
filters = render_article_filters(engine)

# Custom logic
if filters["language"] == "fr" and filters["country"] == "france":
    st.info("🇫🇷 Articles français de France")

# Récupérer articles
articles = get_filtered_articles(engine, filters, limit=100)

# Custom display
for _, article in articles.iterrows():
    with st.expander(f"📄 {article['title']}"):
        st.write(f"**Domaine:** {article['domain']}")
        st.write(f"**Mots:** {article['word_count']:,}")
        st.write(f"**URL:** {article['url']}")
```

#### 🐛 Troubleshooting

**Problème: "Aucun article trouvé"**
- Vérifier que la table `scraped_articles` contient des données
- Vérifier les migrations (migration 005 pour champs Expat.com)
- Assouplir les filtres (mettre "Toutes" partout)

**Problème: "Erreur de connexion DB"**
- Vérifier les variables d'env `POSTGRES_HOST`, `POSTGRES_USER`, etc.
- Tester avec `psql` en ligne de commande

**Problème: "Graphiques non affichés"**
- Installer Plotly : `pip install plotly`
- Le composant fonctionne sans Plotly (stats sans graphiques)

**Problème: "Export CSV vide dans Excel"**
- Le BOM UTF-8 (`\ufeff`) est inclus pour Excel
- Si problème persiste, ouvrir avec "UTF-8" explicite dans Excel

#### 🧪 Tests

Exécuter les tests unitaires:

```bash
cd scraper-pro
python dashboard/test_article_filters.py
```

Les tests vérifient:
- ✅ Connexion à la base de données
- ✅ Récupération des valeurs uniques
- ✅ Construction des requêtes SQL
- ✅ Comptage des articles

#### 📄 Licence

© 2025 Scraper-Pro. Usage interne uniquement.

---

## 🚀 Roadmap

**Prochains composants:**

- [ ] `contact_filters.py` - Filtres pour contacts validés
- [ ] `job_monitor.py` - Monitoring temps-réel des jobs
- [ ] `proxy_dashboard.py` - Dashboard santé des proxies
- [ ] `mailwizz_sync.py` - Stats sync MailWizz

---

## 💬 Support

Pour toute question ou suggestion sur les composants:
- Consulter la doc principale : `scraper-pro/README.md`
- Consulter le guide dashboard : `dashboard/README_FINAL.md`
