# 📚 Scripts Overview - Scraper-Pro

Vue d'ensemble complète de tous les scripts disponibles pour le déploiement, la maintenance et le monitoring de Scraper-Pro.

---

## 📊 Tableau Récapitulatif

| Script | Type | Priorité | Durée | Utilisation |
|--------|------|----------|-------|-------------|
| `quick_install.sh` | Déploiement | **🔴 Critique** | 10-15 min | Installation initiale automatique |
| `validate-installation.sh` | Validation | **🔴 Critique** | 1 min | Vérification post-installation |
| `setup-nginx.sh` | Configuration | **🟡 Important** | 5-10 min | Configuration Nginx + SSL |
| `init-production.sh` | Déploiement | **🟢 Legacy** | 15-20 min | Installation manuelle (déprécié) |
| `backup-postgres.sh` | Maintenance | **🔴 Critique** | 1-2 min | Backup quotidien PostgreSQL |
| `restore-postgres.sh` | Maintenance | **🟡 Important** | 5-10 min | Restauration depuis backup |
| `monitor_job.sh` | Monitoring | **🟢 Utile** | Continu | Surveillance job en temps réel (Bash) |
| `monitor_job.py` | Monitoring | **🟢 Utile** | Continu | Surveillance job en temps réel (Python) |
| `test_deduplication.py` | Test | **🟢 Utile** | 2-3 min | Test du système de déduplication |

---

## 🔴 Scripts Critiques (Must-Have)

### 1. quick_install.sh

**Description :** Installation automatique complète de Scraper-Pro sur un serveur vierge.

**Fonctionnalités :**
- ✅ Installation système (Docker, Docker Compose, Git, UFW)
- ✅ **Auto-génération des secrets cryptographiques**
- ✅ Configuration .env automatique
- ✅ Build et démarrage des containers
- ✅ Validation de l'installation
- ✅ **Sauvegarde des secrets** dans `~/.scraper-pro-secrets-*.txt`

**Usage :**
```bash
# Installation complète (recommandé)
bash scripts/quick_install.sh

# Skiper Docker (si déjà installé)
bash scripts/quick_install.sh --skip-docker

# Nettoyage complet (DESTRUCTIF)
bash scripts/quick_install.sh --cleanup
```

**Secrets auto-générés :**
- `POSTGRES_PASSWORD` : 32 caractères
- `REDIS_PASSWORD` : 32 caractères
- `API_HMAC_SECRET` : 64 caractères
- `DASHBOARD_PASSWORD` : 16 caractères
- `GRAFANA_PASSWORD` : 16 caractères

**Prérequis :**
- Ubuntu 22.04 / Debian 12
- Accès root ou sudo
- Connexion Internet

**Output :**
- ✅ 8 containers démarrés
- ✅ API accessible (http://localhost:8000/health)
- ✅ Fichier de secrets : `~/.scraper-pro-secrets-YYYYMMDD_HHMMSS.txt`

---

### 2. validate-installation.sh

**Description :** Validation automatique de l'installation (20+ checks).

**Fonctionnalités :**
- ✅ Vérifie Docker Daemon
- ✅ Vérifie les 8 containers (postgres, redis, app, dashboard, prometheus, grafana, loki, promtail)
- ✅ Teste les health endpoints
- ✅ Vérifie le schéma PostgreSQL
- ✅ Teste la connectivité réseau
- ✅ Vérifie les ressources (disque, RAM)
- ✅ Vérifie la sécurité (.env permissions, mots de passe par défaut)

**Usage :**
```bash
# Validation standard
bash scripts/validate-installation.sh

# Validation détaillée (verbose)
bash scripts/validate-installation.sh --verbose
```

**Checks effectués :**

| Catégorie | Checks |
|-----------|--------|
| Docker | Daemon, 8 containers |
| Services | API, PostgreSQL, Redis, Dashboard, Grafana, Prometheus |
| Base de données | Tables créées (4 tables minimum) |
| Réseau | API→PostgreSQL, API→Redis |
| Ressources | Disque < 80%, RAM < 80% |
| Sécurité | .env permissions = 600, pas de mots de passe par défaut |

**Output :**
```
=========================================
  Validation Summary
=========================================
Total Checks: 20
Passed: 20

✅ All checks passed! Installation is healthy.
```

**Automatisation (cron) :**
```bash
# Monitoring horaire
crontab -e

# Ajouter :
0 * * * * /opt/scraper-pro/scripts/validate-installation.sh >> /var/log/scraper-health.log 2>&1
```

---

### 3. backup-postgres.sh

**Description :** Backup automatique de PostgreSQL avec compression et rotation.

**Fonctionnalités :**
- ✅ Dump PostgreSQL complet (`pg_dump`)
- ✅ Compression GZIP
- ✅ Rotation (garde 7 jours)
- ✅ Vérification de succès
- ✅ Logging

**Usage :**
```bash
# Backup manuel
bash scripts/backup-postgres.sh

# Automatisation (cron quotidien à 2h)
crontab -e

# Ajouter :
0 2 * * * /opt/scraper-pro/scripts/backup-postgres.sh >> /home/scraper/backup.log 2>&1
```

**Output :**
- Fichier : `/home/scraper/backups/scraper_db_YYYYMMDD_HHMMSS.sql.gz`
- Taille : ~10-100 MB (selon la base)
- Rotation : 7 derniers backups

**Restauration :**
```bash
bash scripts/restore-postgres.sh /home/scraper/backups/scraper_db_20260213_020000.sql.gz
```

---

## 🟡 Scripts Importants (Recommended)

### 4. setup-nginx.sh

**Description :** Configuration automatique de Nginx + SSL Let's Encrypt.

**Fonctionnalités :**
- ✅ Installation Nginx + Certbot
- ✅ Vérification DNS (dig)
- ✅ Configuration reverse proxy (3 sous-domaines)
- ✅ Installation SSL Let's Encrypt
- ✅ Renouvellement automatique (cron)
- ✅ Configuration firewall UFW

**Usage :**
```bash
# Avec domaine
bash scripts/setup-nginx.sh yourdomain.com

# Avec email personnalisé
bash scripts/setup-nginx.sh yourdomain.com admin@yourdomain.com
```

**Prérequis DNS :**

| Nom | Type | Valeur |
|-----|------|--------|
| dashboard.yourdomain.com | A | IP serveur |
| api.yourdomain.com | A | IP serveur |
| grafana.yourdomain.com | A | IP serveur |

**Output :**
- ✅ `https://dashboard.yourdomain.com` → Streamlit
- ✅ `https://api.yourdomain.com` → FastAPI
- ✅ `https://grafana.yourdomain.com` → Grafana

**SSL :**
- Certificats Let's Encrypt (gratuits)
- Renouvellement automatique tous les 60 jours
- Rating SSL Labs : A+

---

### 5. restore-postgres.sh

**Description :** Restauration d'un backup PostgreSQL.

**Usage :**
```bash
# Restaurer un backup
bash scripts/restore-postgres.sh /path/to/backup.sql.gz

# Lister les backups disponibles
ls -lh /home/scraper/backups/
```

**Processus :**
1. Arrête les services
2. Supprime l'ancienne base
3. Recrée la base
4. Restaure le backup
5. Redémarre les services

**Temps :** 5-10 minutes (selon taille)

---

## 🟢 Scripts Utiles (Nice to Have)

### 6. monitor_job.sh (Bash)

**Description :** Surveillance en temps réel d'un job de scraping (version Bash).

**Fonctionnalités :**
- ✅ Affichage du status en temps réel
- ✅ Barre de progression visuelle
- ✅ Compteurs (pages, contacts, erreurs)
- ✅ Détection automatique de fin
- ✅ Rafraîchissement toutes les X secondes

**Usage :**
```bash
# Surveiller un job (rafraîchir toutes les 10s)
./scripts/monitor_job.sh 123

# Intervalle personnalisé (5s)
./scripts/monitor_job.sh 123 5

# API distante
API_URL=http://prod-server:8000 ./scripts/monitor_job.sh 123
```

**Prérequis :**
- `curl` installé
- `jq` installé (optionnel, pour affichage enrichi)

**Output :**
```
[2026-02-13 14:30:45] Rafraîchissement #12
  Status      : ⚙️  RUNNING
  Progress    : [████████████░░░░░░░░] 60.5%
  Pages       : 61
  Contacts    : 23
  Errors      : 0
```

---

### 7. monitor_job.py (Python)

**Description :** Surveillance en temps réel d'un job de scraping (version Python, multi-plateforme).

**Fonctionnalités :**
- ✅ Affichage enrichi avec `rich` (couleurs, tableaux)
- ✅ Barre de progression animée
- ✅ Compatible Windows/Linux/Mac
- ✅ Graphiques ASCII optionnels

**Usage :**
```bash
# Installer dépendances (optionnelles)
pip install requests rich

# Surveiller un job
python scripts/monitor_job.py 123

# Intervalle personnalisé
python scripts/monitor_job.py 123 --interval 5

# API distante
python scripts/monitor_job.py 123 --api-url http://prod-server:8000
```

**Prérequis :**
- Python 3.8+
- `requests` (requis)
- `rich` (optionnel, pour affichage enrichi)

---

### 8. test_deduplication.py

**Description :** Test complet du système de déduplication (URLs, emails, content hash).

**Fonctionnalités :**
- ✅ Teste la déduplication d'URLs (exact + normalized)
- ✅ Teste la déduplication d'emails (global)
- ✅ Teste la déduplication de contenu (hash)
- ✅ Vérifie les tables PostgreSQL
- ✅ Vérifie le cache Redis

**Usage :**
```bash
# Test complet
docker exec scraper-app python scripts/test_deduplication.py

# Test depuis l'hôte (si Python 3.8+ installé)
python scripts/test_deduplication.py
```

**Output :**
```
========================================
  Test de Déduplication - Scraper-Pro
========================================

✅ URL exact match: duplicate detected
✅ URL normalization: http/https treated as same
✅ Email global dedup: duplicate detected
✅ Content hash: similar content detected

========================================
  ✅ All tests passed!
========================================
```

---

## 🟢 Scripts Legacy (Déprécié)

### 9. init-production.sh

**Description :** Installation manuelle (ancienne méthode, avant `quick_install.sh`).

**Statut :** ⚠️ Déprécié, utiliser `quick_install.sh` à la place.

**Différences avec `quick_install.sh` :**
- ❌ Pas d'auto-génération des secrets
- ❌ Configuration manuelle requise
- ❌ Pas de validation automatique

**Usage (déconseillé) :**
```bash
bash scripts/init-production.sh
```

---

## 🔧 Workflow Recommandé

### Installation Initiale

```bash
# 1. Cloner le repo
git clone https://github.com/VOTRE_ORG/scraper-pro.git /opt/scraper-pro
cd /opt/scraper-pro

# 2. Installation automatique
bash scripts/quick_install.sh

# 3. Sauvegarder les secrets
cat ~/.scraper-pro-secrets-*.txt
# Copier dans password manager, puis :
rm ~/.scraper-pro-secrets-*.txt

# 4. Valider l'installation
bash scripts/validate-installation.sh

# 5. Configurer Nginx + SSL (optionnel)
bash scripts/setup-nginx.sh yourdomain.com

# 6. Configurer le backup automatique
crontab -e
# Ajouter : 0 2 * * * /opt/scraper-pro/scripts/backup-postgres.sh >> /home/scraper/backup.log 2>&1
```

---

### Mise à Jour

```bash
# 1. Backup .env
cp /opt/scraper-pro/.env ~/scraper-backup.env

# 2. Backup PostgreSQL
bash scripts/backup-postgres.sh

# 3. Pull les changements
cd /opt/scraper-pro
git pull origin main

# 4. Rebuild et restart
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# 5. Valider
bash scripts/validate-installation.sh
```

---

### Diagnostic

```bash
# 1. Validation complète
bash scripts/validate-installation.sh --verbose

# 2. Logs en temps réel
docker-compose -f docker-compose.production.yml logs -f

# 3. Logs d'un service spécifique
docker logs scraper-app --tail 100

# 4. Monitoring d'un job
./scripts/monitor_job.sh 123
```

---

### Rollback

```bash
# 1. Arrêter les services
cd /opt/scraper-pro
docker-compose -f docker-compose.production.yml down

# 2. Restaurer un backup
bash scripts/restore-postgres.sh /home/scraper/backups/scraper_db_20260213_020000.sql.gz

# 3. Revenir au commit précédent
git log --oneline -10
git checkout COMMIT_ID

# 4. Rebuild et restart
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

---

## 📚 Documentation Complète

Pour plus d'informations :

- **scripts/README.md** : Guide détaillé de chaque script
- **DEPLOYMENT_PRODUCTION.md** : Guide de déploiement complet
- **CHANGELOG_DEPLOYMENT.md** : Historique des améliorations
- **QUICK_START.md** : Guide de démarrage rapide
- **docs/ARCHITECTURE.md** : Architecture technique

---

## 🔒 Checklist de Sécurité

Avant la mise en production :

- [ ] Secrets générés automatiquement (32+ caractères)
- [ ] Fichier `.env` avec permissions 600
- [ ] Backup automatique configuré (cron)
- [ ] SSL/TLS actif (Let's Encrypt)
- [ ] Firewall UFW configuré (ports 22, 80, 443)
- [ ] Monitoring actif (Grafana + Prometheus)
- [ ] Pas de mots de passe par défaut (`grep CHANGE_ME .env`)
- [ ] Secrets sauvegardés dans password manager
- [ ] Validation post-installation passée (20/20 checks)

---

## 🎯 Priorités par Cas d'Usage

### Déploiement Initial (Serveur Vierge)
1. **quick_install.sh** (auto-génère tout)
2. **validate-installation.sh** (vérifie)
3. **setup-nginx.sh** (si domaine disponible)
4. **backup-postgres.sh** (configurer cron)

### Mise en Production
1. **setup-nginx.sh** (SSL obligatoire)
2. **backup-postgres.sh** (backups quotidiens)
3. **validate-installation.sh** (monitoring horaire)

### Debugging
1. **validate-installation.sh --verbose** (diagnostic)
2. **monitor_job.sh** (suivre les jobs)
3. **docker logs** (logs détaillés)

### Monitoring Continu
1. **validate-installation.sh** (cron horaire)
2. **backup-postgres.sh** (cron quotidien)
3. **monitor_job.py** (surveillance jobs)

---

**Scraper-Pro v2.1.0 - Scripts Overview**
Made with ❤️ by the SOS-Expat Tech Team
