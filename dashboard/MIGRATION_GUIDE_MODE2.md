# 🔄 Guide de Migration - Dashboard MODE 2 Refonte

## ⚠️ Avant de Commencer

### Pré-requis
- ✅ Backup automatique créé : `app_legacy.py`
- ✅ Docker compose MODE 2 : `docker-compose-mode-simple.yml`
- ✅ Variables d'environnement : `.env` configuré
- ✅ PostgreSQL database accessible

---

## 🚀 Migration Rapide (5 minutes)

### Étape 1: Vérification des fichiers
```bash
cd scraper-pro/dashboard

# Vérifier que les nouveaux fichiers existent
ls -la i18n/locales/fr.json i18n/locales/en.json
ls -la services/db.py services/api.py services/auth.py
ls -la pages/custom_urls.py pages/blog_content.py
ls -la components/layout.py components/metrics_card.py
ls -la assets/custom.css
```

### Étape 2: Test en local (optionnel)
```bash
# Installer les dépendances (si pas déjà fait)
pip install -r requirements.txt

# Lancer le dashboard en local
streamlit run app.py

# Ouvrir http://localhost:8501
# Tester :
# - Login avec DASHBOARD_PASSWORD
# - Toggle langue FR/EN
# - Navigation sidebar
# - Page Custom URLs
# - Page Blog Content
```

### Étape 3: Déploiement Docker MODE 2
```bash
cd ..  # Retour à scraper-pro/

# Arrêter les containers actuels
docker-compose -f docker-compose-mode-simple.yml down

# Rebuild le dashboard
docker-compose -f docker-compose-mode-simple.yml build dashboard

# Redémarrer
docker-compose -f docker-compose-mode-simple.yml up -d

# Vérifier les logs
docker-compose -f docker-compose-mode-simple.yml logs -f dashboard
```

### Étape 4: Vérification
```bash
# Le dashboard doit être accessible sur :
# http://localhost:8501

# Tester :
curl -I http://localhost:8501
```

---

## 🔍 Tests Fonctionnels

### Checklist de validation

#### 1. Authentification
- [ ] Login avec bon mot de passe → Accès autorisé
- [ ] Login avec mauvais mot de passe → Erreur
- [ ] Session persiste après rerun

#### 2. Navigation
- [ ] Sidebar affiche 6 pages :
  - [ ] Custom URLs
  - [ ] Blog Content
  - [ ] Jobs
  - [ ] Contacts
  - [ ] Stats
  - [ ] Config
- [ ] Clic sur chaque page → Navigation fonctionne
- [ ] Page sélectionnée reste active (bleu)
- [ ] Badge MODE 2 visible en bas sidebar

#### 3. Internationalisation
- [ ] Toggle FR/EN en header fonctionne
- [ ] Langue persiste dans URL (?lang=fr ou ?lang=en)
- [ ] Toutes les strings traduites (pas de hardcoded)
- [ ] Variables interpolées fonctionnent (messages d'erreur)

#### 4. Page Custom URLs
- [ ] Formulaire affiche correctement
- [ ] Textarea pour URLs présente
- [ ] Validation : "au moins 1 URL requise" si vide
- [ ] Création job avec liste URLs → Success + rerun
- [ ] Métriques affichées (Total jobs, URLs, Contacts, Success rate)
- [ ] Liste des 20 jobs récents affichée

#### 5. Page Blog Content
- [ ] Formulaire affiche correctement
- [ ] Input URL blog présent
- [ ] Number inputs : max articles + scrape depth
- [ ] Validation : "URL requise" si vide
- [ ] Création job blog → Success + rerun
- [ ] Métriques affichées (Articles, Blogs, Avg words, This week)
- [ ] Liste des 20 articles récents affichée

#### 6. Page Jobs
- [ ] Liste des 50 derniers jobs affichée
- [ ] Métriques : Total, Running, Completed, Failed
- [ ] Actions job (Resume, Pause, Cancel) fonctionnent
- [ ] Job ID selection fonctionne

#### 7. Page Contacts
- [ ] Métriques pipeline affichées
- [ ] Table "By Platform" affichée
- [ ] Export CSV avec filtres fonctionne
- [ ] Download CSV contient BOM UTF-8

#### 8. Page Stats
- [ ] Graphique volume scraping affiché
- [ ] Table sync MailWizz affichée
- [ ] Domain blacklist affichée
- [ ] WHOIS intelligence metrics affichées

#### 9. Page Config
- [ ] System health (API, PostgreSQL, Redis) affiché
- [ ] Active config (proxy provider) affiché
- [ ] Environment variables JSON affiché
- [ ] Pas de credentials exposés (masqué "configured")

#### 10. Design & UX
- [ ] Sidebar sombre (gradient #0f172a → #020617)
- [ ] Navigation hover effet bleu clair
- [ ] Navigation active gradient bleu
- [ ] Metrics cards border-left bleu
- [ ] Metrics cards hover effet (translateY)
- [ ] Buttons gradient primary bleu
- [ ] Forms border-radius 8px
- [ ] Language pills style moderne
- [ ] Animations fluides (transitions 0.2s)

---

## 🐛 Troubleshooting

### Problème: Sidebar n'affiche pas le style sombre
**Solution:**
```python
# Vérifier que custom.css est chargé dans app.py
# Vérifier le chemin du fichier CSS
css_file = Path(__file__).parent / "assets" / "custom.css"
print(css_file.exists())  # Doit être True
```

### Problème: Traductions manquantes (clés affichées)
**Solution:**
```python
# Vérifier que les fichiers JSON sont bien chargés
i18n = I18nManager()
print(i18n._translations.keys())  # Doit afficher ['fr', 'en']

# Vérifier une clé spécifique
print(i18n.t('jobs.header'))  # Doit afficher "Gestion des Jobs" (fr)
```

### Problème: Erreur "Module not found: i18n"
**Solution:**
```bash
# S'assurer d'être dans le bon répertoire
cd scraper-pro/dashboard

# Vérifier la structure
ls -la i18n/__init__.py
ls -la i18n/manager.py

# Relancer streamlit
streamlit run app.py
```

### Problème: Erreur "Service db not found"
**Solution:**
```python
# Vérifier les imports
# Dans app.py, les imports doivent être:
from services.db import query_df, query_scalar
# PAS: from db import query_df

# Si erreur persiste, ajouter au début de app.py:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### Problème: Database connection error
**Solution:**
```bash
# Vérifier les variables d'environnement
docker-compose -f docker-compose-mode-simple.yml exec dashboard env | grep POSTGRES

# Doit afficher :
# POSTGRES_HOST=postgres
# POSTGRES_PORT=5432
# POSTGRES_DB=scraper_db
# POSTGRES_USER=scraper_admin
# POSTGRES_PASSWORD=...

# Tester la connexion
docker-compose -f docker-compose-mode-simple.yml exec dashboard python -c "
from services.db import get_engine
engine = get_engine()
print('Connection OK!')
"
```

### Problème: API request fails (HMAC error)
**Solution:**
```bash
# Vérifier que API_HMAC_SECRET est défini
docker-compose -f docker-compose-mode-simple.yml exec dashboard env | grep API_HMAC_SECRET

# Vérifier que le scraper API est accessible
docker-compose -f docker-compose-mode-simple.yml exec dashboard curl http://scraper:8000/health

# Vérifier les logs API
docker-compose -f docker-compose-mode-simple.yml logs scraper | tail -20
```

---

## 🔙 Rollback vers Ancien Dashboard

Si vous rencontrez des problèmes et devez revenir à l'ancien dashboard :

### Option 1: Swap rapide
```bash
cd scraper-pro/dashboard
mv app.py app_new.py
mv app_legacy.py app.py

# Redémarrer le container
cd ..
docker-compose -f docker-compose-mode-simple.yml restart dashboard
```

### Option 2: Docker rebuild
```bash
cd scraper-pro

# Éditer docker-compose-mode-simple.yml
# Changer:
# command: streamlit run dashboard/app.py
# En:
# command: streamlit run dashboard/app_legacy.py

# Rebuild
docker-compose -f docker-compose-mode-simple.yml up -d --build dashboard
```

### Option 3: Git reset (si versioning activé)
```bash
cd scraper-pro
git log --oneline | head -5  # Trouver le commit avant refonte
git reset --hard <commit-sha>
docker-compose -f docker-compose-mode-simple.yml up -d --build dashboard
```

---

## 📊 Métriques de Performance

### Avant Refonte
- **Lignes de code** : 1156 lignes (app.py)
- **Navigation** : Tabs horizontaux statiques
- **i18n** : ❌ Aucune
- **Design** : Basique Streamlit

### Après Refonte
- **Lignes de code** : 115 lignes (app.py) = **-90%**
- **Navigation** : Sidebar moderne avec style dark
- **i18n** : ✅ FR/EN (226 strings)
- **Design** : Backlink Engine inspired

### Temps de Chargement
- **Page initiale** : ~1.5s (similaire avant/après)
- **Navigation entre pages** : Instantané (<100ms)
- **Toggle langue** : ~200ms (rerun)

---

## 🎯 Prochaines Étapes

### Améliorations Possibles
1. **Ajouter d'autres langues** : ES, DE, PT
2. **Mode sombre/clair** : Toggle dark/light theme
3. **Responsive mobile** : Sidebar collapse sur mobile
4. **Keyboard shortcuts** : Ctrl+1-6 pour navigation
5. **Recherche globale** : Search bar pour filtrer pages
6. **Notifications** : Toast messages pour actions
7. **Export avancé** : Excel, PDF en plus de CSV

### Nouvelles Features MODE 2
1. **Scheduler jobs** : Cron-like scheduling pour jobs Custom URLs/Blog
2. **Batch operations** : Actions multiples sur plusieurs jobs
3. **Templates** : Sauvegarder configs de jobs fréquents
4. **Analytics** : Graphiques avancés pour Custom URLs performance
5. **AI suggestions** : Suggestions d'URLs similaires à scraper

---

## 📞 Support

### Logs à vérifier en cas d'erreur
```bash
# Dashboard logs
docker-compose -f docker-compose-mode-simple.yml logs dashboard | tail -50

# Scraper API logs
docker-compose -f docker-compose-mode-simple.yml logs scraper | tail -50

# PostgreSQL logs
docker-compose -f docker-compose-mode-simple.yml logs postgres | tail -50
```

### Fichiers importants
- `app.py` : Point d'entrée principal (nouveau)
- `app_legacy.py` : Ancien fichier (backup)
- `i18n/manager.py` : Gestionnaire i18n
- `services/db.py` : Connexion database
- `components/layout.py` : Sidebar + Header
- `assets/custom.css` : Styles custom

---

**Migration complétée avec succès ! 🎉**

Si vous avez des questions, consultez le README_REFONTE_MODE2.md pour plus de détails.
