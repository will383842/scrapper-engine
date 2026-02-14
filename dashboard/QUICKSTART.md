# 🚀 Quick Start Guide - Dashboard Final

Démarrez avec le dashboard Scraper-Pro en 5 minutes chrono!

---

## ⚡ Installation Express (Windows)

```powershell
# 1. Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate

# 2. Installer les dépendances
pip install -r dashboard\requirements.txt

# 3. Configurer les variables d'environnement
copy .env.example .env
# Éditez .env avec vos vraies valeurs

# 4. Lancer le dashboard
streamlit run dashboard\app_final.py
```

**Le dashboard sera accessible sur:** `http://localhost:8501`

---

## ⚡ Installation Express (Linux/Mac)

```bash
# 1. Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 2. Installer les dépendances
pip install -r dashboard/requirements.txt

# 3. Configurer les variables d'environnement
cp .env.example .env
# Éditez .env avec vos vraies valeurs

# 4. Lancer le dashboard
streamlit run dashboard/app_final.py
```

**Le dashboard sera accessible sur:** `http://localhost:8501`

---

## 🐳 Installation Express (Docker)

```bash
# 1. Build l'image
docker-compose -f docker-compose.production.yml build dashboard

# 2. Lancer le container
docker-compose -f docker-compose.production.yml up -d dashboard

# 3. Vérifier les logs
docker-compose -f docker-compose.production.yml logs -f dashboard
```

**Le dashboard sera accessible sur:** `http://localhost:8501`

---

## 🔑 Configuration Minimale (.env)

Créez un fichier `.env` à la racine du projet avec ces variables:

```bash
# ═══ OBLIGATOIRES ═══
DASHBOARD_PASSWORD=mon_password_admin_securise
API_HMAC_SECRET=mon_secret_hmac_tres_long_et_securise

# ═══ DATABASE ═══
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=scraper_db
POSTGRES_USER=scraper_admin
POSTGRES_PASSWORD=mon_password_postgres

# ═══ API ═══
SCRAPER_API_URL=http://localhost:8000

# ═══ MODE ═══
SCRAPING_MODE=urls_only
```

### 🔐 Générer des Secrets Sécurisés

```bash
# Linux/Mac
openssl rand -hex 32

# Python (Windows/Linux/Mac)
python -c "import secrets; print(secrets.token_hex(32))"

# PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
```

---

## ✅ Vérification de l'Installation

### Test 1: Connexion au Dashboard

```bash
# Ouvrir dans le navigateur
http://localhost:8501

# Entrer le mot de passe (DASHBOARD_PASSWORD)
# Vous devriez voir 7 onglets:
# - 📄 Scraping URLs
# - 🔍 Scraping Google
# - 👥 Contacts & Articles
# - 📈 Statistiques
# - 🌐 Proxies Health
# - 🔎 WHOIS Lookup
# - ⚙️ Configuration
```

### Test 2: Santé des Services

Dans la **sidebar**, vérifiez:
- ✅ API Opérationnelle (vert)
- ✅ PostgreSQL OK (vert)
- ✅ Redis OK (vert)

Si tout est vert, vous êtes prêt! 🎉

### Test 3: Script Automatisé

```bash
# Lancer le script de test
python dashboard/test_dashboard.py

# Vous devriez voir:
# ✅ Environment Variables - PASSED
# ✅ Python Dependencies - PASSED
# ✅ Dashboard File - PASSED
# ✅ Database Connection - PASSED
# ✅ API Connection - PASSED
```

---

## 🎯 Premiers Pas

### 1. Créer votre Premier Job

1. Aller dans l'onglet **📄 Scraping URLs**
2. Cliquer sur **📝 Formulaire de Création** (expander)
3. Remplir:
   - **Nom:** "Test Job"
   - **Type:** URLs Personnalisées
   - **URLs:** Collez quelques URLs (une par ligne)
   - **Catégorie:** Choisir ou laisser Auto-detect
   - **Plateforme:** Choisir ou laisser Auto-detect
4. Cliquer **🚀 Lancer le Job**

### 2. Suivre le Job en Temps Réel

- La liste des jobs se rafraîchit automatiquement
- Regardez la colonne **Progress** (barre de progression)
- Status possible: 🟢 Running, ✅ Completed, ❌ Failed

### 3. Voir les Résultats

1. Onglet **👥 Contacts & Articles** > Sub-tab **📧 Contacts**
2. Voir le nombre de contacts scrapés, validés, envoyés
3. Utiliser la recherche pour trouver un contact spécifique
4. Exporter en CSV si besoin

### 4. Analyser les Stats

1. Onglet **📈 Statistiques**
2. Voir le graphique de volume (30 derniers jours)
3. Analyser la répartition par plateforme
4. Vérifier les domaines blacklistés

---

## 🚨 Résolution Rapide de Problèmes

### ❌ "Cannot connect to database"

**Solution:**
```bash
# Vérifier PostgreSQL
docker-compose ps postgres
# Ou
sudo systemctl status postgresql

# Vérifier les variables
echo $POSTGRES_HOST
echo $POSTGRES_PASSWORD

# Tester connexion
psql -h localhost -U scraper_admin -d scraper_db
```

### ❌ "API error: connection refused"

**Solution:**
```bash
# Vérifier l'API
curl http://localhost:8000/health

# Vérifier SCRAPER_API_URL dans .env
cat .env | grep SCRAPER_API_URL
```

### ❌ "Invalid password"

**Solution:**
```bash
# Vérifier DASHBOARD_PASSWORD dans .env
# Pas d'espaces avant/après
# Exemple correct:
# DASHBOARD_PASSWORD=mon_password_123

# Exemple incorrect:
# DASHBOARD_PASSWORD = mon_password_123  ❌ (espaces)
```

### 🐌 Dashboard lent

**Solution:**
```bash
# Cliquer sur le bouton 🔄 Rafraîchir
# Ou redémarrer Streamlit
Ctrl+C
streamlit run dashboard/app_final.py
```

---

## 📚 Documentation Complète

Pour aller plus loin:

- **README Complet:** `dashboard/README_FINAL.md`
- **Guide de Migration:** `dashboard/MIGRATION_GUIDE.md`
- **Code Source:** `dashboard/app_final.py`

---

## 🎓 Tutoriel Vidéo (à venir)

Suivez notre tutoriel vidéo étape par étape:
1. Installation de A à Z
2. Configuration des variables d'environnement
3. Création du premier job
4. Analyse des résultats
5. Export des données

---

## 💡 Astuces Pro

### Raccourcis Clavier Streamlit

- `R` - Relancer l'app (après modification du code)
- `C` - Ouvrir settings
- `⌘+K` ou `Ctrl+K` - Menu de recherche

### Performance

Pour améliorer la performance:

1. **Ajoutez des index DB:**
   ```sql
   CREATE INDEX idx_jobs_status ON scraping_jobs(status);
   CREATE INDEX idx_jobs_created ON scraping_jobs(created_at DESC);
   ```

2. **Activez le cache Streamlit:**
   - Déjà activé sur `get_engine()`
   - Ajoutez `@st.cache_data` sur vos queries custom

3. **Limitez les résultats:**
   - Toutes les queries ont déjà des LIMIT (50-100)
   - Utilisez les filtres pour affiner

### Customization

Pour personnaliser le dashboard:

1. **Modifier les couleurs CSS** (ligne 43-124 de `app_final.py`)
2. **Ajouter des métriques custom** (ligne 380+ pour chaque onglet)
3. **Créer des onglets custom** (ligne 274)

---

## 🆘 Support

**Problème non résolu?**

1. Consulter `dashboard/README_FINAL.md` section Troubleshooting
2. Vérifier les logs: `docker-compose logs dashboard`
3. Tester avec `python dashboard/test_dashboard.py`
4. Créer une issue GitHub avec:
   - OS et version Python
   - Logs d'erreur complets
   - Steps to reproduce

---

## 🎉 Félicitations!

Vous êtes maintenant prêt à utiliser le dashboard Scraper-Pro!

**Prochaines étapes:**
1. ✅ Créer vos premiers jobs de scraping
2. ✅ Explorer tous les onglets
3. ✅ Configurer les alertes (à venir)
4. ✅ Passer en mode production (HTTPS, monitoring)

**Bon scraping! 🚀**

---

**Made with ❤️ by Ultra-Professional Team**

**Version:** 1.0
**Date:** 2025-02-13
**Support:** README_FINAL.md
