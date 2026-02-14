# 🚀 Scraper-Pro Dashboard - Refonte MODE 2 avec i18n

## 📋 Vue d'ensemble

Refonte complète du dashboard Scraper-Pro MODE 2 avec :
- ✅ **Sidebar navigation moderne** (style Backlink Engine)
- ✅ **Internationalisation FR/EN** (226+ strings traduites)
- ✅ **Architecture modulaire** (pages/components/services séparés)
- ✅ **Design ultra-moderne** avec animations et thème sombre
- ✅ **Focus MODE 2** : Custom URLs + Blog Content (pas Google Search/Maps)
- ✅ **Badge MODE SIMPLE** visible en sidebar
- ✅ **Code réduit de 90%** : 115 lignes vs 1156 lignes

---

## 📁 Nouvelle Architecture

```
dashboard/
├── app.py                      # Main entry (~115 lignes, -90%)
├── app_legacy.py               # Ancien app.py (backup)
│
├── i18n/                       # Internationalisation
│   ├── __init__.py
│   ├── manager.py              # Classe I18nManager
│   └── locales/
│       ├── fr.json             # 226 strings français
│       └── en.json             # 226 strings anglais
│
├── services/                   # Services métier
│   ├── __init__.py
│   ├── db.py                   # Database helpers
│   ├── api.py                  # API client (HMAC)
│   └── auth.py                 # Authentification
│
├── components/                 # Composants UI réutilisables
│   ├── __init__.py
│   ├── layout.py               # Sidebar + Header
│   ├── metrics_card.py         # Cartes métriques
│   └── article_filters.py      # Filtres articles (existant)
│
├── pages/                      # Pages séparées
│   ├── __init__.py
│   ├── custom_urls.py          # 🆕 Page Custom URLs (MODE 2)
│   ├── blog_content.py         # 🆕 Page Blog Content (MODE 2)
│   ├── jobs.py                 # Page Jobs refactorisée
│   ├── contacts.py             # Page Contacts refactorisée
│   ├── stats.py                # Page Stats refactorisée
│   └── config.py               # Page Config refactorisée
│
└── assets/                     # Assets statiques
    └── custom.css              # 🆕 Backlink Engine style
```

---

## 🎨 Design System

### Palette de couleurs
```python
COLORS = {
    'brand': {
        'primary': '#1b6ff5',      # Blue primary
        'accent': '#59b2ff',       # Light blue accents
    },
    'surface': {
        'dark': '#0f172a',         # Sidebar background
        'darker': '#020617',       # Very dark sections
        'light': '#f8fafc',        # Main content background
        'card': '#ffffff',         # Cards background
    },
    'text': {
        'dark': '#1e293b',         # Main text on light
        'light': '#f8fafc',        # Text on dark sidebar
        'muted': '#64748b',        # Secondary text
    },
    'status': {
        'success': '#10b981',
        'warning': '#f59e0b',
        'error': '#ef4444',
        'info': '#3b82f6',
    }
}
```

### Layout
```
┌────────────────────────────────────────────────────────────┐
│  Header: Logo + Page Title + Language Toggle (FR/EN)      │
├──────────┬─────────────────────────────────────────────────┤
│          │                                                 │
│ Sidebar  │  Main Content Area                             │
│ (Dark)   │  ┌──────────────────────────────────────────┐  │
│          │  │  Metrics Cards (4 columns)               │  │
│ • Custom │  ├──────────────────────────────────────────┤  │
│   URLs   │  │                                          │  │
│ • Blog   │  │  Data Table / Forms                      │  │
│ • Jobs   │  │                                          │  │
│ • Contact│  └──────────────────────────────────────────┘  │
│ • Stats  │                                                 │
│ • Config │                                                 │
│          │                                                 │
│ [MODE 2] │                                                 │
│  Badge   │                                                 │
└──────────┴─────────────────────────────────────────────────┘
```

---

## 🌍 Système i18n

### Utilisation dans le code

```python
from i18n.manager import I18nManager

i18n = I18nManager(default_lang='fr')

# Simple traduction
i18n.t('jobs.header')  # → "Gestion des Jobs"

# Avec variables
i18n.t('messages.error', error='Connection failed')
# → "Erreur : Connection failed"

# Nested keys
i18n.t('customUrls.metrics.totalJobs')  # → "Jobs Total"

# Changer la langue
i18n.set_language('en')
i18n.t('jobs.header')  # → "Jobs Management"
```

### Structure des fichiers JSON

```json
{
  "jobs": {
    "header": "Gestion des Jobs",
    "metrics": {
      "total": "Total Jobs",
      "running": "En cours"
    }
  },
  "messages": {
    "error": "Erreur : {error}",
    "jobCreated": "Job créé ! ID: {job_id}"
  }
}
```

---

## 🆕 Pages MODE 2 (Nouvelles)

### 1. Custom URLs (`pages/custom_urls.py`)
Page dédiée au scraping d'URLs personnalisées :
- ✅ Formulaire avec textarea pour liste d'URLs
- ✅ Métriques : Total jobs, URLs scrapées, contacts trouvés, taux succès
- ✅ Sélection catégorie + plateforme + auto-injection
- ✅ Liste des 20 jobs custom_urls récents
- ✅ Validation : au moins 1 URL requise

### 2. Blog Content (`pages/blog_content.py`)
Page dédiée au scraping de blogs :
- ✅ Formulaire avec URL blog + max articles + scrape depth
- ✅ Métriques : Articles scrapés, blogs uniques, mots moyens, cette semaine
- ✅ Liste des 20 articles récents
- ✅ Validation : URL requise

---

## 🔄 Pages Refactorisées

### Jobs (`pages/jobs.py`)
- Liste des 50 derniers jobs
- Métriques : Total, Running, Completed, Failed
- Actions : Resume, Pause, Cancel
- i18n complète

### Contacts (`pages/contacts.py`)
- Pipeline de contacts scrapés/validés
- Métriques : Scraped, Validated, Sent to MailWizz, Bounced
- Export CSV avec filtres (status, platform, category)
- i18n complète

### Stats (`pages/stats.py`)
- Volume scraping quotidien (30j)
- Sync MailWizz quotidienne (30j)
- Domain blacklist
- WHOIS intelligence
- i18n complète

### Config (`pages/config.py`)
- System health (API, PostgreSQL, Redis)
- Configuration active (proxy provider, MailWizz routing)
- Environment variables
- i18n complète

---

## 🛠️ Services Modulaires

### Database (`services/db.py`)
```python
from services.db import query_df, query_scalar

# Requête retournant une liste de dicts
jobs = query_df("SELECT * FROM scraping_jobs LIMIT 10")

# Requête retournant une valeur scalaire
count = query_scalar("SELECT COUNT(*) FROM contacts")
```

### API Client (`services/api.py`)
```python
from services.api import api_request

# POST avec HMAC signature
result = api_request("POST", "/api/v1/scraping/jobs", {
    "source_type": "custom_urls",
    "name": "My Job",
    "config": {"urls": ["https://example.com"]}
})
```

### Auth (`services/auth.py`)
```python
from services.auth import check_authentication

if not check_authentication(i18n):
    st.stop()  # Affiche formulaire login
```

---

## 🎯 Comparaison Avant/Après

| Aspect | Avant | Après | Amélioration |
|--------|-------|-------|--------------|
| **Lignes de code (app.py)** | 1156 | 115 | 🔥 **-90%** |
| **Navigation** | Tabs horizontaux | Sidebar dark moderne | ✨ **UX++** |
| **i18n** | ❌ Français hardcodé | ✅ FR/EN (226 strings) | 🌍 **i18n** |
| **Architecture** | Monolithique | Modulaire | 📦 **Modulaire** |
| **Design** | Basique | Backlink Engine style | 🎨 **Moderne** |
| **MODE 2 Support** | Tabs confusion | Pages dédiées | 🎯 **Focus** |
| **Badge MODE** | ❌ Inexistant | ✅ Visible sidebar | 🏷️ **Clarté** |

---

## 🚀 Démarrage

### 1. Installation
```bash
cd scraper-pro/dashboard
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copier .env example
cp ../.env.mode2.example ../.env

# Définir le mot de passe
echo "DASHBOARD_PASSWORD=votremotdepasse" >> ../.env
```

### 3. Lancement
```bash
# Avec Docker Compose MODE 2
cd ..
docker-compose -f docker-compose-mode-simple.yml up -d

# Ou en local
streamlit run dashboard/app.py
```

### 4. Accès
- URL : http://localhost:8501
- Login avec le mot de passe défini dans `.env`
- Sélectionner langue : FR 🇫🇷 ou EN 🇬🇧

---

## ✅ Critères de Validation (Complétés)

### Fonctionnels
- [x] Navigation sidebar fonctionne (6 pages MODE 2)
- [x] Toggle langue FR/EN avec persistance URL
- [x] Formulaire Custom URLs crée job
- [x] Formulaire Blog Content crée job
- [x] Toutes les métriques s'affichent
- [x] Export CSV fonctionne
- [x] Authentification fonctionne

### UX/Design
- [x] Sidebar sombre (Backlink Engine style) ✨
- [x] Animations fluides (hover, transitions)
- [x] Badge MODE 2 visible en sidebar
- [x] Metrics cards avec border coloré
- [x] Buttons avec gradient primary
- [x] Language toggle pills style

### i18n
- [x] 226 strings traduites FR + EN
- [x] Aucun hardcoded string restant
- [x] Variables interpolées fonctionnent
- [x] Nested keys résolues
- [x] Fallback langue

### Architecture
- [x] Code réduit de 90% (1156 → 115 lignes)
- [x] Séparation pages/components/services
- [x] Imports propres
- [x] Navigation claire

---

## 📝 Notes Importantes

### MODE 2 - Simplifications
- ❌ **Pas de Google Search** : Non supporté en MODE 2
- ❌ **Pas de Google Maps** : Non supporté en MODE 2
- ✅ **Custom URLs uniquement** : Focus principal
- ✅ **Blog Content uniquement** : Focus secondaire

### Migration depuis ancien dashboard
Si vous utilisez l'ancien dashboard :
1. L'ancien fichier est sauvegardé dans `app_legacy.py`
2. Les données DB restent compatibles
3. Les variables d'environnement restent identiques
4. Pas de downtime nécessaire

### Rollback si besoin
```bash
cd scraper-pro/dashboard
mv app.py app_new.py
mv app_legacy.py app.py
```

---

## 🎓 Pour aller plus loin

### Ajouter une nouvelle langue
1. Créer `dashboard/i18n/locales/es.json`
2. Copier la structure de `fr.json`
3. Traduire toutes les clés
4. Ajouter dans `render_language_switcher()` :
```python
langs = {'fr': '🇫🇷 FR', 'en': '🇬🇧 EN', 'es': '🇪🇸 ES'}
```

### Ajouter une nouvelle page
1. Créer `dashboard/pages/ma_page.py`
2. Définir fonction `render_ma_page(i18n)`
3. Ajouter dans `app.py` :
```python
from pages.ma_page import render_ma_page

PAGES = {
    ...
    'ma_page': {
        'title': i18n.t('pages.maPage.title'),
        'render': render_ma_page
    }
}
```
4. Ajouter dans sidebar (`components/layout.py`) :
```python
pages = {
    ...
    'ma_page': {'icon': '🔥', 'label': i18n.t('sidebar.maPage')}
}
```

---

## 📞 Support

- **Documentation** : Ce fichier + commentaires inline
- **Issues** : Vérifier `app_legacy.py` pour comparaison
- **Architecture** : Voir schéma ci-dessus

---

**Fait avec ❤️ pour les expats** 🌍
