# 🚀 QUICK START - Scraper-Pro Ultra-Professional

Guide ultra-rapide pour démarrer en **moins de 10 minutes**.

---

## 📋 PRÉREQUIS

- Serveur Ubuntu 22.04 / Debian 12
- 8GB RAM minimum (CPX31 recommandé)
- Accès SSH root ou sudo

---

## ⚡ INSTALLATION EN 3 COMMANDES

```bash
# 1. Cloner le projet
git clone https://github.com/YOUR_REPO/scraper-pro.git
cd scraper-pro

# 2. Installer automatiquement
bash scripts/quick_install.sh

# 3. Éditer les secrets
nano .env
```

**C'est tout!** Le système est prêt.

---

## 🔒 CONFIGURATION MINIMALE

Éditez `.env` et remplacez ces valeurs:

```bash
# Passwords (32+ caractères recommandés)
POSTGRES_PASSWORD=CHANGE_ME
REDIS_PASSWORD=CHANGE_ME
DASHBOARD_PASSWORD=CHANGE_ME

# API Secret (64 caractères recommandés)
API_HMAC_SECRET=CHANGE_ME

# MailWizz (si vous avez déjà les clés)
MAILWIZZ_SOS_EXPAT_API_KEY=your_key
MAILWIZZ_ULIXAI_API_KEY=your_key
```

**Générer des secrets forts:**

```bash
# PostgreSQL password
openssl rand -base64 32

# Redis password
openssl rand -base64 32

# API HMAC secret (64 chars)
openssl rand -hex 32
```

---

## 🎯 ACCÈS AU SYSTÈME

### Dashboard Premium
```
http://YOUR_SERVER_IP:8501
```

**Login:** Mot de passe depuis `DASHBOARD_PASSWORD`

### API Backend
```
http://YOUR_SERVER_IP:8000/health
```

### Grafana (Monitoring)
```
http://YOUR_SERVER_IP:3000
```

**Login:** `admin` / `GRAFANA_PASSWORD` (depuis `.env`)

---

## ✅ VÉRIFICATION

```bash
# Vérifier les containers
docker ps

# Health check API
curl http://localhost:8000/health
# Résultat attendu: {"status": "ok", "postgres": true, "redis": true}

# Tester la déduplication
docker exec scraper-app python scripts/test_deduplication.py
# Résultat attendu: 8/8 tests passed (100%)
```

---

## 🎉 PREMIER JOB DE SCRAPING

### Via Dashboard

1. Aller sur `http://YOUR_SERVER_IP:8501`
2. Se connecter
3. Tab **"Scraping URLs (Actif)"**
4. Section **"Lancer un Nouveau Job"**
5. Remplir:
   - **Type**: URLs Personnalisées
   - **URLs**: Coller vos URLs (une par ligne)
   - **Plateforme**: `sos-expat` ou `ulixai`
6. Cliquer **"Lancer le Job"**

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/scraping/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Test Job",
    "config": {
      "urls": [
        "https://example.com",
        "https://example2.com"
      ]
    },
    "platform": "sos-expat",
    "auto_inject_mailwizz": false
  }'
```

---

## 📊 STATISTIQUES DE DÉDUPLICATION

### Dashboard Premium

1. Tab **"Scraping URLs (Actif)"**
2. Section **"Déduplication Ultra-Professionnelle"**

Métriques affichées:
- 🔗 URLs Exactes dédupliquées
- 🌐 URLs Normalisées dédupliquées
- 📧 Emails Uniques
- 📄 Contenus Uniques
- Taux de déduplication global (%)

### PostgreSQL

```bash
# Voir les stats en temps réel
docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c "SELECT * FROM deduplication_stats;"
```

### Redis

```bash
# Voir les clés de déduplication
docker exec scraper-redis redis-cli -a YOUR_PASSWORD KEYS "dedup:*"

# Nombre d'emails uniques
docker exec scraper-redis redis-cli -a YOUR_PASSWORD SCARD "dedup:email:global"
```

---

## 🔧 COMMANDES UTILES

### Logs

```bash
# Tous les logs
docker-compose -f docker-compose.production.yml logs -f

# Logs d'un service spécifique
docker logs scraper-app -f
docker logs scraper-postgres -f
docker logs scraper-dashboard -f
```

### Restart

```bash
# Restart tous les services
docker-compose -f docker-compose.production.yml restart

# Restart un service spécifique
docker restart scraper-app
```

### Stop / Start

```bash
# Stop
docker-compose -f docker-compose.production.yml down

# Start
docker-compose -f docker-compose.production.yml up -d
```

### Rebuild (après modifications)

```bash
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

---

## 🌐 EXPOSITION PUBLIQUE (Nginx + SSL)

### 1. Installer Nginx

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 2. Configurer le Dashboard

```bash
sudo nano /etc/nginx/sites-available/scraper-dashboard
```

**Contenu:**

```nginx
server {
    listen 80;
    server_name dashboard.yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Activer

```bash
sudo ln -s /etc/nginx/sites-available/scraper-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. SSL avec Let's Encrypt

```bash
sudo certbot --nginx -d dashboard.yourdomain.com
```

**Répéter pour API et Grafana** (voir `DEPLOYMENT_PRODUCTION.md`)

---

## 🔄 MIGRATION VERS MODE FULL (Google)

Quand vous êtes prêt à activer Google Search et Google Maps:

### 1. Souscrire aux Services

- **Proxy Provider**: Oxylabs, BrightData, ou SmartProxy (~€500-2000/mois)
- **SerpAPI**: https://serpapi.com (~€50-200/mois)

### 2. Modifier `.env`

```bash
nano .env
```

**Changer:**

```bash
# Passer en mode full
SCRAPING_MODE=full

# Configurer les proxies
PROXY_PROVIDER=oxylabs
PROXY_USER=your_username
PROXY_PASS=your_password

# Ajouter SerpAPI
SERPAPI_KEY=your_key
```

### 3. Restart

```bash
docker-compose -f docker-compose.production.yml restart
```

### 4. Vérifier

Dashboard → Tab **"Scraping Google"** (maintenant actif)

---

## 📚 DOCUMENTATION COMPLÈTE

- **[ULTRA_PRO_SYSTEM_READY.md](ULTRA_PRO_SYSTEM_READY.md)**: Vue d'ensemble complète
- **[DEPLOYMENT_PRODUCTION.md](DEPLOYMENT_PRODUCTION.md)**: Guide de déploiement détaillé (600+ lignes)
- **[docs/DEDUPLICATION_SYSTEM.md](docs/DEDUPLICATION_SYSTEM.md)**: Documentation déduplication (700+ lignes)
- **[config/scraping_modes.json](config/scraping_modes.json)**: Configuration des modes

---

## 🐛 PROBLÈMES COURANTS

### Container ne démarre pas

```bash
# Voir les logs
docker logs scraper-app

# Vérifier la config
docker-compose -f docker-compose.production.yml config
```

### PostgreSQL connection refused

```bash
# Vérifier que PostgreSQL est démarré
docker ps | grep postgres

# Tester la connexion
docker exec scraper-postgres pg_isready -U scraper_admin
```

### Redis connection refused

```bash
# Vérifier que Redis est démarré
docker ps | grep redis

# Tester la connexion
docker exec scraper-redis redis-cli -a YOUR_PASSWORD ping
```

### Dashboard inaccessible

```bash
# Vérifier les logs
docker logs scraper-dashboard

# Attendre 1-2 minutes (Streamlit startup)
```

---

## 💡 TIPS

### Augmenter la Performance

```bash
# .env
CONCURRENT_REQUESTS=32          # (default: 16)
DOWNLOAD_DELAY=0.5              # (default: 1.0)
SMART_THROTTLE_MIN_DELAY=0.25   # (default: 0.5)
```

### Backup Manuel

```bash
# PostgreSQL
docker exec scraper-postgres pg_dump -U scraper_admin scraper_db | gzip > backup.sql.gz

# Restore
gunzip < backup.sql.gz | docker exec -i scraper-postgres psql -U scraper_admin scraper_db
```

### Cleanup Déduplication

```bash
# PostgreSQL
docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c "SELECT cleanup_expired_deduplication_cache();"

# Redis
docker exec scraper-redis redis-cli -a YOUR_PASSWORD FLUSHALL
```

---

## 🎉 SUCCÈS!

Votre système Scraper-Pro Ultra-Professional est maintenant **100% opérationnel**.

**Prochaines étapes:**
1. Créer votre premier job de scraping
2. Vérifier les stats de déduplication
3. Configurer les backups automatiques
4. Mettre en place Nginx + SSL pour l'accès public

**Bon scraping!** 🚀

---

**Scraper-Pro v2.0.0 - Ultra-Professional System**
