# 📦 Guide d'Installation - Scraper-Pro

Guide complet pour installer et configurer **Scraper-Pro** en production.

---

## 📋 Prérequis Système

### Matériel minimum

| Ressource | Minimum | Recommandé |
|-----------|---------|------------|
| **CPU** | 2 cores | 4 cores |
| **RAM** | 4 GB | 8 GB |
| **Disque** | 20 GB SSD | 50 GB SSD |
| **Réseau** | 10 Mbps | 100 Mbps |

### Logiciels requis

```bash
# Docker Engine 20.10+
docker --version
# Docker version 20.10.21, build baeda1f

# Docker Compose 2.0+
docker-compose --version
# Docker Compose version v2.15.1

# Git
git --version
# git version 2.39.0
```

---

## 🚀 Installation Pas-à-Pas

### Étape 1 : Cloner le repository

```bash
# Clone avec SSH (recommandé)
git clone git@github.com:votre-org/scraper-pro.git
cd scraper-pro

# OU avec HTTPS
git clone https://github.com/votre-org/scraper-pro.git
cd scraper-pro
```

### Étape 2 : Configuration de l'environnement

```bash
# Copier le template
cp .env.example .env

# Éditer avec votre éditeur préféré
nano .env  # ou vim, code, etc.
```

#### 2.1 - Configurer PostgreSQL

```bash
# Générer un mot de passe sécurisé
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}"

# Ajouter dans .env
POSTGRES_DB=scraper_db
POSTGRES_USER=scraper_admin
POSTGRES_PASSWORD=VOTRE_MDP_GENERE
```

#### 2.2 - Configurer Redis

```bash
# Générer un mot de passe sécurisé
REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "REDIS_PASSWORD=${REDIS_PASSWORD}"

# Ajouter dans .env
REDIS_PASSWORD=VOTRE_MDP_REDIS_GENERE
```

#### 2.3 - Configurer les Proxies

##### Option A : Oxylabs (Recommandé)

```bash
# Dans .env
PROXY_PROVIDER=oxylabs
PROXY_USER=customer-YOUR_USERNAME
PROXY_PASS=YOUR_PASSWORD
```

Obtenir vos credentials :
1. Aller sur [https://oxylabs.io](https://oxylabs.io)
2. Dashboard → Proxies → Credentials
3. Copier Username et Password

##### Option B : BrightData

```bash
PROXY_PROVIDER=brightdata
PROXY_USER=lum-customer-YOUR_CUSTOMER-zone-YOUR_ZONE
PROXY_PASS=YOUR_PASSWORD
```

##### Option C : SmartProxy

```bash
PROXY_PROVIDER=smartproxy
PROXY_USER=YOUR_USERNAME
PROXY_PASS=YOUR_PASSWORD
```

#### 2.4 - Configurer MailWizz

##### SOS-Expat

```bash
# Dans .env
MAILWIZZ_SOS_EXPAT_API_URL=https://mail.sos-expat.com/api
MAILWIZZ_SOS_EXPAT_API_KEY=YOUR_API_KEY
```

Obtenir la clé API :
1. Connexion MailWizz SOS-Expat
2. Paramètres → API Keys → Create new
3. Copier la clé publique

##### Ulixai

```bash
# Dans .env
MAILWIZZ_ULIXAI_API_URL=https://mail.ulixai.com/api
MAILWIZZ_ULIXAI_API_KEY=YOUR_API_KEY
```

#### 2.5 - Configurer les Webhooks

```bash
# Générer les secrets HMAC
WEBHOOK_SOS_EXPAT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
WEBHOOK_ULIXAI_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Dans .env
WEBHOOK_SOS_EXPAT_URL=https://us-central1-sos-urgently-ac307.cloudfunctions.net/emailEventsWebhook
WEBHOOK_SOS_EXPAT_SECRET=${WEBHOOK_SOS_EXPAT_SECRET}

WEBHOOK_ULIXAI_URL=https://api.ulixai.com/webhooks/email-events
WEBHOOK_ULIXAI_SECRET=${WEBHOOK_ULIXAI_SECRET}
```

⚠️ **Important** : Configurer ces mêmes secrets dans vos Cloud Functions !

#### 2.6 - Configurer l'authentification API

```bash
# Générer un secret HMAC sécurisé (64 caractères)
API_HMAC_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
echo "API_HMAC_SECRET=${API_HMAC_SECRET}"

# Ajouter dans .env
API_HMAC_SECRET=VOTRE_SECRET_API_GENERE
```

#### 2.7 - Configurer le Dashboard

```bash
# Choisir un mot de passe admin sécurisé
DASHBOARD_PASSWORD=VotreMotDePasseAdmin2024!

# Ajouter dans .env
DASHBOARD_PASSWORD=${DASHBOARD_PASSWORD}
```

#### 2.8 - Configurer SerpAPI (Optionnel mais recommandé)

Pour contourner les CAPTCHA Google :

```bash
# 1. Créer un compte sur https://serpapi.com
# 2. Dashboard → API Key
# 3. Copier la clé

# Dans .env
SERPAPI_KEY=YOUR_SERPAPI_KEY_HERE
```

### Étape 3 : Configurer les fichiers JSON

#### 3.1 - Configuration Proxies

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
    "max_consecutive_failures": 5,
    "cooldown_minutes": [5, 10, 20, 30],
    "max_cooldowns_before_blacklist": 5
  },
  "rate_limiting": {
    "default_delay_seconds": 2.0,
    "per_domain_limits": {
      "google.com": 5.0,
      "google.fr": 5.0,
      "maps.google.com": 5.0
    }
  }
}
```

#### 3.2 - Configuration MailWizz Routing

Vérifier `config/mailwizz_routing.json` :

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
        // ... autres catégories
      }
    },
    "ulixai": {
      "lists": {
        "blogueur": {
          "list_id": 1,
          "list_name": "Blogueurs Voyage",
          "auto_tags": ["blogueur", "content_creator", "voyage"],
          "template_default": "affiliation_75pct"
        }
        // ... autres catégories
      }
    }
  }
}
```

⚠️ **Important** : Adapter les `list_id` à vos vraies listes MailWizz !

### Étape 4 : Initialiser la base de données

```bash
# Démarrer seulement PostgreSQL
docker-compose up -d postgres

# Attendre que PostgreSQL soit prêt (10-15 secondes)
sleep 15

# Vérifier le statut
docker-compose logs postgres | grep "database system is ready"

# Initialiser le schéma
docker-compose exec postgres psql -U scraper_admin -d scraper_db -f /docker-entrypoint-initdb.d/01-init.sql

# Appliquer les migrations
docker-compose exec postgres psql -U scraper_admin -d scraper_db < db/migrations/002_add_checkpoint_resume.sql
docker-compose exec postgres psql -U scraper_admin -d scraper_db < db/migrations/003_add_scraped_articles.sql
docker-compose exec postgres psql -U scraper_admin -d scraper_db < db/migrations/004_add_compound_indexes.sql
```

### Étape 5 : Démarrer tous les services

```bash
# Démarrer en mode détaché
docker-compose up -d

# Vérifier que tous les services sont up
docker-compose ps

# Résultat attendu :
# NAME                  STATUS              PORTS
# scraper-postgres      Up (healthy)        127.0.0.1:5432->5432/tcp
# scraper-redis         Up (healthy)        127.0.0.1:6379->6379/tcp
# scraper-app           Up                  127.0.0.1:8000->8000/tcp
# scraper-dashboard     Up                  127.0.0.1:8501->8501/tcp
# scraper-prometheus    Up                  127.0.0.1:9090->9090/tcp
# scraper-grafana       Up                  127.0.0.1:3000->3000/tcp
# scraper-loki          Up                  127.0.0.1:3100->3100/tcp
```

### Étape 6 : Vérifier l'installation

#### 6.1 - Santé de l'API

```bash
curl http://localhost:8000/health

# Réponse attendue :
{
  "status": "ok",
  "service": "scraper-pro",
  "postgres": true,
  "redis": true
}
```

#### 6.2 - Accès Dashboard

Ouvrir : http://localhost:8501

Mot de passe : `DASHBOARD_PASSWORD` défini dans `.env`

#### 6.3 - Vérifier les logs

```bash
# Logs du scraper
docker-compose logs -f scraper

# Logs PostgreSQL
docker-compose logs postgres

# Logs de tous les services
docker-compose logs
```

---

## 🔧 Configuration Post-Installation

### 1. Configurer les Backups

```bash
# Créer le répertoire de backup
sudo mkdir -p /var/backups/scraper-pro
sudo chown $USER:$USER /var/backups/scraper-pro

# Ajouter le cron de backup (exécuté tous les jours à 3h00)
crontab -e

# Ajouter cette ligne :
0 3 * * * /c/Users/willi/Documents/Projets/VS_CODE/scraper-pro/scripts/backup-postgres.sh
```

### 2. Configurer Grafana

```bash
# Accéder à Grafana
open http://localhost:3000

# Login : admin / GRAFANA_PASSWORD (défini dans .env)

# Importer les dashboards :
# 1. Settings → Data Sources → Add Prometheus (http://prometheus:9090)
# 2. Dashboards → Import → Upload dashboards/scraper-pro.json
```

### 3. Tester le système end-to-end

```bash
# Créer un job de test
curl -X POST http://localhost:8000/api/v1/scraping/jobs \
  -H "Content-Type: application/json" \
  -H "X-Timestamp: $(date +%s)" \
  -H "X-Signature: $(echo -n "$(date +%s).{}" | openssl dgst -sha256 -hmac "$(grep API_HMAC_SECRET .env | cut -d= -f2)" | awk '{print $2}')" \
  -d '{
    "source_type": "custom_urls",
    "name": "Test Installation",
    "config": {
      "urls": ["https://example.com"]
    },
    "category": null,
    "platform": null,
    "tags": ["test"],
    "auto_inject_mailwizz": false
  }'

# Vérifier dans le dashboard que le job est créé
```

---

## 🐛 Troubleshooting Installation

### Problème 1 : PostgreSQL ne démarre pas

```bash
# Vérifier les logs
docker-compose logs postgres

# Erreur commune : "permission denied"
# Solution : Réinitialiser les volumes
docker-compose down -v
docker-compose up -d postgres
```

### Problème 2 : Redis connection refused

```bash
# Vérifier que Redis tourne
docker-compose ps redis

# Tester la connexion
docker-compose exec redis redis-cli -a "$(grep REDIS_PASSWORD .env | cut -d= -f2)" ping

# Résultat attendu : PONG
```

### Problème 3 : API retourne 503 "Database not configured"

```bash
# Vérifier les variables d'environnement
docker-compose exec scraper env | grep POSTGRES

# Redémarrer le scraper
docker-compose restart scraper
```

### Problème 4 : Dashboard Streamlit ne charge pas

```bash
# Vérifier les logs
docker-compose logs dashboard

# Vérifier la connexion DB
docker-compose exec dashboard python -c "
from sqlalchemy import create_engine
import os
url = f'postgresql://{os.getenv(\"POSTGRES_USER\")}:{os.getenv(\"POSTGRES_PASSWORD\")}@postgres:5432/{os.getenv(\"POSTGRES_DB\")}'
engine = create_engine(url)
conn = engine.connect()
print('✓ Database connected')
"
```

### Problème 5 : Les proxies ne fonctionnent pas

```bash
# Tester manuellement
docker-compose exec scraper python -c "
import os
import httpx
proxy = f'http://{os.getenv(\"PROXY_USER\")}:{os.getenv(\"PROXY_PASS\")}@pr.oxylabs.io:7777'
try:
    r = httpx.get('http://ip-api.com/json', proxies={'http://': proxy}, timeout=10)
    print('✓ Proxy works:', r.json()['query'])
except Exception as e:
    print('✗ Proxy error:', e)
"
```

---

## 📚 Prochaines étapes

Après l'installation :

1. 📖 Lire [ARCHITECTURE.md](ARCHITECTURE.md) pour comprendre le système
2. 🔌 Lire [API.md](API.md) pour l'utilisation de l'API
3. 🚀 Lire [DEPLOYMENT.md](DEPLOYMENT.md) pour le déploiement production
4. 📊 Configurer les dashboards Grafana
5. 🔔 Configurer les alertes (email/Slack)

---

## ✅ Checklist d'Installation

```
Installation Checklist
======================

Prérequis
□ Docker 20.10+ installé
□ Docker Compose 2.0+ installé
□ Git installé
□ Compte proxy (Oxylabs/BrightData/SmartProxy)
□ Accès API MailWizz (SOS-Expat + Ulixai)
□ Compte SerpAPI (optionnel)

Configuration
□ Repository cloné
□ .env créé et configuré
□ POSTGRES_PASSWORD généré (32+ chars)
□ REDIS_PASSWORD généré (32+ chars)
□ API_HMAC_SECRET généré (48+ chars)
□ WEBHOOK secrets générés (32+ chars)
□ Proxies configurés dans .env
□ MailWizz API keys configurés
□ SerpAPI key configuré (optionnel)
□ config/proxy_config.json vérifié
□ config/mailwizz_routing.json adapté

Démarrage
□ PostgreSQL démarré et healthy
□ Redis démarré et healthy
□ Base de données initialisée
□ Migrations appliquées
□ Scraper démarré
□ Dashboard démarré
□ Prometheus démarré
□ Grafana démarré

Vérification
□ API /health retourne "ok"
□ Dashboard accessible (http://localhost:8501)
□ Grafana accessible (http://localhost:3000)
□ Backups configurés
□ Job de test créé et réussi
□ Logs visibles et propres

Post-Installation
□ Dashboards Grafana importés
□ Alertes configurées
□ Monitoring vérifié
□ Documentation lue
□ Équipe formée
```

---

**Installation réussie ? 🎉** Passez à [l'utilisation du système](../README.md#-utilisation) !
