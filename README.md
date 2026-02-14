# 🔍 Scraper-Pro

**Système professionnel de scraping B2B avec pipeline complet de validation, catégorisation et injection MailWizz.**

[![Production Ready](https://img.shields.io/badge/production-ready-green.svg)](https://github.com)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://docs.docker.com/compose/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

---

## 🎉 Nouveautés v1.1.0

**Mode Dev API** - Démarrez en 5 minutes sans configuration HMAC !

```bash
# Créer un job de scraping en une seule commande
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Mon Premier Job",
    "config": {"urls": ["https://example.com"]}
  }'

# Surveiller en temps réel
./scripts/monitor_job.sh 123
```

**Nouveautés :**
- 🆕 Endpoint `/jobs/simple` sans authentification (localhost uniquement)
- 🆕 Endpoint `/logs` pour consulter les erreurs détaillées
- 🆕 Scripts de monitoring (Bash + Python)
- 📖 Guide Quick Start - Premier job en 5 minutes
- 📖 Documentation enrichie avec 45+ exemples

**Liens rapides :**
- 📖 [Quick Start Guide](docs/API_QUICKSTART.md) - Démarrage en 5 minutes
- 🛠️ [Mode Dev API](docs/API_DEV_MODE.md) - Guide complet
- 🆕 [Release Notes v1.1](RELEASE_NOTES_v1.1.md) - Détails complets

---

## 📋 Table des matières

- [Vue d'ensemble](#-vue-densemble)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [API Reference](#-api-reference)
- [Monitoring](#-monitoring)
- [Backups](#-backups)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🎯 Vue d'ensemble

**Scraper-Pro** automatise l'acquisition de contacts professionnels B2B via 4 sources :
- 🔎 **Google Search** : Recherche par mots-clés avec pagination
- 📍 **Google Maps** : Extraction de business listings
- 🔗 **URLs personnalisées** : Scraping de listes ciblées
- 📝 **Blog Content** : Extraction d'articles de blog

Le système inclut un **pipeline complet** :
```
Scraping → Validation → Catégorisation → Enrichissement → Injection MailWizz
```

### Technologies utilisées

| Composant | Stack |
|-----------|-------|
| **Scraping** | Scrapy 2.11, SerpAPI (fallback anti-CAPTCHA) |
| **API** | FastAPI 0.115, Uvicorn |
| **Database** | PostgreSQL 16, Redis 7 |
| **Dashboard** | Streamlit 1.41 |
| **Monitoring** | Prometheus, Grafana, Loki |
| **Orchestration** | Docker Compose |
| **Tests** | Pytest, pytest-asyncio |

---

## ✨ Fonctionnalités

### 🕷️ Scraping Multi-Sources
- ✅ 4 spiders opérationnels avec checkpoint/resume
- ✅ Proxies rotatifs (Oxylabs, BrightData, SmartProxy)
- ✅ Anti-ban : User-agent rotation, delays, rate limiting
- ✅ SerpAPI fallback pour contourner CAPTCHA Google
- ✅ Extraction : emails, téléphones, réseaux sociaux, WHOIS

### ✅ Validation Robuste
- ✅ Email : Regex + DNS MX check + blacklist domaines jetables
- ✅ Téléphone : Validation internationale avec `phonenumbers`
- ✅ Déduplication : Redis atomic + PostgreSQL UNIQUE
- ✅ Blacklist domaines : Bounce rate > 10%

### 🎯 Catégorisation Automatique
- ✅ **14 catégories** : avocat, assureur, médecin, blogueur, etc.
- ✅ Scoring intelligent : Keywords + source_type
- ✅ Routing multi-plateforme : SOS-Expat vs Ulixai
- ✅ Tags auto-générés

### 📧 Intégration MailWizz
- ✅ Client API complet (add/update/search)
- ✅ 21 listes configurées (catégories professionnelles)
- ✅ Warmup Guard : Protection quotas email
- ✅ Retry logic : 3 tentatives avec backoff
- ✅ Webhooks : Bounce/open/click notifications

### 📊 Dashboard Administrateur
- ✅ 6 onglets : Jobs, Contacts, Articles, Stats, WHOIS, Config
- ✅ Création de jobs en 1 clic
- ✅ Monitoring temps réel
- ✅ Exports CSV/JSON
- ✅ Recherche et filtres avancés

### 🔐 Sécurité
- ✅ HMAC-SHA256 authentication (API)
- ✅ Rate limiting (protection DDoS)
- ✅ Environment variables pour secrets
- ✅ Docker network isolation
- ✅ Port binding `127.0.0.1` uniquement

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       SCRAPER-PRO                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐  │
│  │   Scrapy     │───>│  PostgreSQL  │<──│  Dashboard   │  │
│  │   Spiders    │    │   (16 GB)    │   │  Streamlit   │  │
│  └──────────────┘    └──────────────┘   └──────────────┘  │
│         │                    │                   │          │
│         │                    │                   │          │
│         v                    v                   v          │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐  │
│  │    Redis     │    │   FastAPI    │   │ Prometheus   │  │
│  │   Cache      │<───│     API      │───│   Grafana    │  │
│  └──────────────┘    └──────────────┘   └──────────────┘  │
│         │                    │                              │
│         │                    │                              │
│         v                    v                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Cron Jobs (process + sync)                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    External Services                        │
├─────────────────────────────────────────────────────────────┤
│  Proxies (Oxylabs) │ MailWizz API │ SerpAPI │ WHOIS       │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline de traitement

```
1. SCRAPING
   ├─ Spider scrape les URLs
   ├─ Extraction contacts (email, phone, social)
   ├─ Checkpoint sauvegardé (reprise auto)
   └─ Stockage dans scraped_contacts (status: pending_validation)

2. VALIDATION (Cron: toutes les heures)
   ├─ Email: Regex + MX check + blacklist
   ├─ Téléphone: phonenumbers validation
   ├─ Déduplication: Redis + DB
   └─ Stockage dans validated_contacts (status: ready_for_mailwizz)

3. CATÉGORISATION
   ├─ Analyse keywords + source_type
   ├─ Scoring (14 catégories)
   ├─ Routing plateforme (SOS-Expat/Ulixai)
   └─ Assignation MailWizz list_id

4. SYNC MAILWIZZ (Cron: toutes les heures, +30min)
   ├─ Batch de 100 contacts
   ├─ Warmup guard check
   ├─ API call avec retry logic
   └─ Update status: sent_to_mailwizz
```

---

## 🚀 Installation

### Prérequis

- Docker 20.10+ et Docker Compose 2.0+
- Git
- 4 GB RAM minimum (8 GB recommandé)
- 20 GB espace disque

### Installation rapide

```bash
# 1. Cloner le repository
git clone https://github.com/votre-org/scraper-pro.git
cd scraper-pro

# 2. Copier et configurer .env
cp .env.example .env
nano .env  # Remplir avec vos vraies valeurs

# 3. Démarrer les services
docker-compose up -d

# 4. Vérifier le statut
docker-compose ps

# 5. Voir les logs
docker-compose logs -f scraper

# 6. Accéder au dashboard
# http://localhost:8501
# Mot de passe : celui défini dans DASHBOARD_PASSWORD
```

### Installation détaillée

Voir [INSTALLATION.md](docs/INSTALLATION.md) pour :
- Configuration des proxies
- Configuration MailWizz
- Configuration monitoring
- Configuration backups

---

## ⚙️ Configuration

### Variables d'environnement essentielles

```bash
# PostgreSQL
POSTGRES_DB=scraper_db
POSTGRES_USER=scraper_admin
POSTGRES_PASSWORD=VOTRE_MOT_DE_PASSE_SECURISE

# Redis
REDIS_PASSWORD=VOTRE_MOT_DE_PASSE_REDIS

# Proxies (au moins un provider)
PROXY_PROVIDER=oxylabs
PROXY_USER=votre_username
PROXY_PASS=votre_password

# MailWizz - SOS-Expat
MAILWIZZ_SOS_EXPAT_API_URL=https://mail.sos-expat.com/api
MAILWIZZ_SOS_EXPAT_API_KEY=votre_api_key

# MailWizz - Ulixai
MAILWIZZ_ULIXAI_API_URL=https://mail.ulixai.com/api
MAILWIZZ_ULIXAI_API_KEY=votre_api_key

# Webhooks
WEBHOOK_SOS_EXPAT_URL=https://us-central1-sos-urgently-ac307.cloudfunctions.net/emailEventsWebhook
WEBHOOK_SOS_EXPAT_SECRET=votre_hmac_secret

# API Authentication
API_HMAC_SECRET=VOTRE_SECRET_HMAC_256_BITS

# Dashboard
DASHBOARD_PASSWORD=admin_password_securise

# Optionnel : SerpAPI (fallback anti-CAPTCHA)
SERPAPI_KEY=votre_serpapi_key
```

### Configuration des proxies

Éditer `config/proxy_config.json` :

```json
{
  "providers": {
    "oxylabs": {
      "endpoint": "pr.oxylabs.io:7777",
      "auth_type": "user_pass",
      "pool_size": 20,
      "type": "datacenter"
    }
  },
  "rotation": {
    "mode": "weighted_random",
    "sticky_session_seconds": 180,
    "max_consecutive_failures": 5
  }
}
```

### Configuration MailWizz routing

Éditer `config/mailwizz_routing.json` pour mapper catégories → listes :

```json
{
  "platforms": {
    "sos-expat": {
      "lists": {
        "avocat": {
          "list_id": 1,
          "list_name": "Avocats Internationaux",
          "auto_tags": ["avocat", "professionnel", "juridique"],
          "template_default": "partenariat_avocat"
        }
      }
    }
  }
}
```

---

## 📖 Utilisation

### 1. Via Dashboard (Recommandé)

1. Accéder à `http://localhost:8501`
2. Se connecter avec `DASHBOARD_PASSWORD`
3. Onglet **Jobs** → **Launch New Job**
4. Sélectionner source type (Google Search, Google Maps, etc.)
5. Configurer paramètres (query, max_results, category, platform)
6. Cliquer **Launch Job**
7. Suivre le progrès en temps réel

### 2. Via API

#### Créer un job

```bash
# Générer signature HMAC
TIMESTAMP=$(date +%s)
BODY='{"source_type":"google_search","name":"Test Job","config":{"query":"avocat Paris","max_results":100},"category":"avocat","platform":"sos-expat","tags":[],"auto_inject_mailwizz":true}'
SIGNATURE=$(echo -n "${TIMESTAMP}.${BODY}" | openssl dgst -sha256 -hmac "VOTRE_API_HMAC_SECRET" | awk '{print $2}')

# Appeler l'API
curl -X POST http://localhost:8000/api/v1/scraping/jobs \
  -H "Content-Type: application/json" \
  -H "X-Timestamp: ${TIMESTAMP}" \
  -H "X-Signature: ${SIGNATURE}" \
  -d "${BODY}"
```

#### Reprendre un job échoué

```bash
curl -X POST http://localhost:8000/api/v1/scraping/jobs/123/resume \
  -H "X-Timestamp: ${TIMESTAMP}" \
  -H "X-Signature: ${SIGNATURE}"
```

#### Voir le statut d'un job

```bash
curl http://localhost:8000/api/v1/scraping/jobs/123/status \
  -H "X-Timestamp: ${TIMESTAMP}" \
  -H "X-Signature: ${SIGNATURE}"
```

### 3. Via CLI (Manuel)

```bash
# Lancer un spider manuellement
docker-compose exec scraper scrapy crawl google_search \
  -a job_id=999 \
  -a query="médecin francophone" \
  -a max_results=50 \
  -a country=fr

# Lancer process_contacts manuellement
docker-compose exec scraper python -m scraper.jobs.process_contacts

# Lancer sync_to_mailwizz manuellement
docker-compose exec scraper python -m scraper.jobs.sync_to_mailwizz
```

---

## 📊 Monitoring

### Dashboards disponibles

| Service | URL | Credentials |
|---------|-----|-------------|
| **Dashboard Scraper** | http://localhost:8501 | `DASHBOARD_PASSWORD` |
| **Grafana** | http://localhost:3000 | admin / `GRAFANA_PASSWORD` |
| **Prometheus** | http://localhost:9090 | - |
| **API Health** | http://localhost:8000/health | - |

### Métriques clés

```bash
# Vérifier la santé du système
curl http://localhost:8000/health

# Réponse attendue :
{
  "status": "ok",
  "service": "scraper-pro",
  "postgres": true,
  "redis": true
}
```

### Alertes configurées

- ✅ Job échoué 3 fois consécutivement
- ✅ PostgreSQL down > 2 minutes
- ✅ Redis down > 1 minute
- ✅ Espace disque < 10%
- ✅ Taux d'erreur scraping > 50%
- ✅ Bounce rate MailWizz > 5%

---

## 💾 Backups

### Backup automatique

Les backups PostgreSQL sont automatiques **tous les jours à 3h00 AM** :

```bash
# Voir les backups disponibles
ls -lh /var/backups/scraper-pro/

# Exemple de sortie :
-rw-r--r-- 1 root root 45M Feb 13 03:00 scraper_db_2026-02-13_030000.sql.gz
-rw-r--r-- 1 root root 43M Feb 12 03:00 scraper_db_2026-02-12_030000.sql.gz
```

### Restauration manuelle

```bash
# Arrêter les services
docker-compose down

# Restaurer depuis un backup
gunzip < /var/backups/scraper-pro/scraper_db_2026-02-13_030000.sql.gz | \
  docker-compose exec -T postgres psql -U scraper_admin -d scraper_db

# Redémarrer
docker-compose up -d
```

### Backup manuel

```bash
# Créer un backup immédiat
docker-compose exec postgres pg_dump -U scraper_admin scraper_db | \
  gzip > backup_manual_$(date +%Y%m%d_%H%M%S).sql.gz
```

---

## 🔧 Troubleshooting

### Problèmes courants

#### 1. Container PostgreSQL ne démarre pas

```bash
# Vérifier les logs
docker-compose logs postgres

# Solution : Réinitialiser le volume
docker-compose down -v
docker-compose up -d
```

#### 2. Spider bloqué par CAPTCHA

```bash
# Vérifier si SerpAPI est configuré
grep SERPAPI_KEY .env

# Solution : Ajouter SERPAPI_KEY dans .env
SERPAPI_KEY=votre_cle_serpapi
```

#### 3. MailWizz sync échoue

```bash
# Vérifier la configuration
docker-compose exec scraper python -c "
from scraper.integrations.mailwizz_client import get_client
client = get_client('sos-expat')
print('✓ MailWizz configured')
"

# Vérifier les logs de sync
docker-compose exec scraper tail -f /app/logs/mailwizz_sync.log
```

#### 4. Dashboard inaccessible

```bash
# Vérifier que le service tourne
docker-compose ps dashboard

# Redémarrer le dashboard
docker-compose restart dashboard
```

#### 5. Proxies ne fonctionnent pas

```bash
# Tester la connexion proxy
docker-compose exec scraper python -c "
import os
import httpx
proxy_url = f'http://{os.getenv(\"PROXY_USER\")}:{os.getenv(\"PROXY_PASS\")}@pr.oxylabs.io:7777'
r = httpx.get('http://ip-api.com/json', proxies={'http://': proxy_url}, timeout=10)
print(r.json())
"
```

### Logs utiles

```bash
# Logs du scraper
docker-compose logs -f scraper

# Logs PostgreSQL
docker-compose logs -f postgres

# Logs Redis
docker-compose logs -f redis

# Logs du dashboard
docker-compose logs -f dashboard

# Logs de tous les services
docker-compose logs -f
```

---

## 🧪 Tests

### Lancer les tests

```bash
# Tous les tests
docker-compose exec scraper pytest

# Avec coverage
docker-compose exec scraper pytest --cov=scraper --cov-report=html

# Tests spécifiques
docker-compose exec scraper pytest tests/test_validator.py -v
```

### Tests disponibles

- `test_api.py` : Tests API REST
- `test_validator.py` : Validation email/phone
- `test_categorizer.py` : Catégorisation
- `test_mailwizz_client.py` : Client MailWizz
- `test_spiders.py` : Spiders Scrapy
- `test_pipelines.py` : Pipelines de traitement
- Et 10 autres fichiers...

---

## 📚 Documentation complète

### Démarrage Rapide
- 🚀 **[API Quick Start](docs/API_QUICKSTART.md)** - Premier job en 5 minutes
- 🛠️ **[Mode Dev API](docs/API_DEV_MODE.md)** - Développement sans HMAC
- 🆕 **[Release Notes v1.1](RELEASE_NOTES_v1.1.md)** - Nouveautés et changements

### Documentation Technique
- 📖 [Guide d'installation détaillé](docs/INSTALLATION.md)
- 🏗️ [Architecture technique](docs/ARCHITECTURE.md)
- 🔌 [API Reference complète](docs/API.md)
- 🔧 [Configuration avancée](docs/CONFIGURATION.md)
- 🚀 [Guide de déploiement](docs/DEPLOYMENT.md)
- 🐛 [Guide de debugging](docs/DEBUGGING.md)

### Changelogs
- 📝 [Changelog API](CHANGELOG_API.md) - Historique API
- 📝 [Changelog Deployment](CHANGELOG_DEPLOYMENT.md) - Déploiement
- 📝 [Changelog Metadata](CHANGELOG_METADATA.md) - Métadonnées

---

## 📄 License

Proprietary - SOS-Expat / Ulixai © 2024-2026

---

## 👥 Support

- 📧 Email : support@sos-expat.com
- 💬 Slack : #scraper-pro
- 🐛 Issues : GitHub Issues

---

**Made with ❤️ by the SOS-Expat Tech Team**
