# 🏗️ Configuration Dual System (2 VPS séparés)

## Architecture recommandée pour isolation maximale

---

## 📋 SYSTÈME 1 : Scraping URLs (CPX21 - 7.39€/mois)

### Specs VPS
- **Provider** : Hetzner Cloud
- **Modèle** : CPX21
- **CPU** : 3 vCPU
- **RAM** : 4 GB
- **Disque** : 80 GB SSD
- **Localisation** : Nuremberg, Germany
- **Prix** : 7.39€/mois

### Services actifs

```yaml
# docker-compose-urls.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: scraper_urls
      POSTGRES_USER: scraper
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_urls_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"

  scraper:
    build: .
    environment:
      DATABASE_URL: postgresql://scraper:${POSTGRES_PASSWORD}@postgres:5432/scraper_urls
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      PROXY_ENABLED: "false"  # ⚠️ PAS de proxies
      DOWNLOAD_DELAY: "2.0"
      CONCURRENT_REQUESTS: "6"
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"

  dashboard:
    build:
      context: ./dashboard
    environment:
      DATABASE_URL: postgresql://scraper:${POSTGRES_PASSWORD}@postgres:5432/scraper_urls
    ports:
      - "3000:3000"
    depends_on:
      - postgres
```

### Configuration .env

```bash
# .env pour Système 1 (URLs)

# Database
POSTGRES_DB=scraper_urls
POSTGRES_USER=scraper
POSTGRES_PASSWORD=VotreMotDePasseFort123!

# Redis
REDIS_PASSWORD=VotreRedisPassword456!

# API
API_HOST=0.0.0.0
API_PORT=8000
API_HMAC_SECRET=VotreSecretHMAC789!

# Scraping (PAS de proxies)
PROXY_ENABLED=false
DOWNLOAD_DELAY=2.0
CONCURRENT_REQUESTS=6
CONCURRENT_REQUESTS_PER_DOMAIN=2

# Rate limiting
DOWNLOAD_TIMEOUT=30
AUTOTHROTTLE_ENABLED=true
AUTOTHROTTLE_START_DELAY=2
AUTOTHROTTLE_MAX_DELAY=30

# Monitoring (minimal)
LOG_LEVEL=INFO
```

### Commandes de déploiement

```bash
# 1. SSH vers VPS 1
ssh root@95.216.123.45

# 2. Installation
cd /opt
git clone https://github.com/VOTRE-USERNAME/scraper-pro.git scraper-urls
cd scraper-urls

# 3. Configuration
cp .env.example .env
nano .env  # Remplir les valeurs

# 4. Utiliser docker-compose allégé
cp docker-compose-urls.yml docker-compose.yml

# 5. Démarrer
docker compose up -d

# 6. Vérifier
docker compose ps
curl http://localhost:8000/health
```

### API Endpoints

```bash
# Base URL
http://95.216.123.45:8000

# Créer job de scraping URLs
curl -X POST http://95.216.123.45:8000/api/v1/scraping/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "urls",
    "urls": [
      "https://www.expat.com/fr/guide/",
      "https://blog.exemple.com/articles/"
    ],
    "extract_content": true,
    "max_results": 10000
  }'

# Dashboard Streamlit
http://95.216.123.45:3000
```

### Monitoring

**Logs :**
```bash
docker compose logs -f scraper
docker compose logs -f postgres
```

**Métriques basiques :**
```bash
# Via Dashboard Streamlit (port 3000)
# Onglets disponibles :
# - Jobs : liste des jobs, statuts
# - Contacts : contacts scrapés
# - Stats : statistiques globales
```

**Pas de Grafana/Prometheus** (économie RAM)

---

## 📋 SYSTÈME 2 : Scraping Google (CPX31 - 11.90€/mois)

### Specs VPS
- **Provider** : Hetzner Cloud
- **Modèle** : CPX31
- **CPU** : 4 vCPU
- **RAM** : 8 GB
- **Disque** : 160 GB SSD
- **Localisation** : Nuremberg, Germany
- **Prix** : 11.90€/mois

### Services actifs

```yaml
# docker-compose-google.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: scraper_google
      POSTGRES_USER: scraper
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_google_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"

  scraper:
    build: .
    environment:
      DATABASE_URL: postgresql://scraper:${POSTGRES_PASSWORD}@postgres:5432/scraper_google
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      PROXY_ENABLED: "true"  # ⚠️ Proxies activés
      PROXY_POOL: '["http://user-country-fr:${SMARTPROXY_PASSWORD}@gate.smartproxy.com:7000"]'
      DOWNLOAD_DELAY: "5.0"  # Plus lent pour Google
      CONCURRENT_REQUESTS: "4"
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"

  dashboard:
    build:
      context: ./dashboard
    environment:
      DATABASE_URL: postgresql://scraper:${POSTGRES_PASSWORD}@postgres:5432/scraper_google
    ports:
      - "3000:3000"
    depends_on:
      - postgres

  # Monitoring complet
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./monitoring/grafana:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    depends_on:
      - prometheus

  loki:
    image: grafana/loki:latest
    volumes:
      - ./monitoring/loki:/etc/loki
      - loki_data:/loki
    ports:
      - "3100:3100"

  alertmanager:
    image: prom/alertmanager:latest
    volumes:
      - ./monitoring/alertmanager:/etc/alertmanager
    ports:
      - "9093:9093"
```

### Configuration .env

```bash
# .env pour Système 2 (Google)

# Database
POSTGRES_DB=scraper_google
POSTGRES_USER=scraper
POSTGRES_PASSWORD=VotreAutreMotDePasse123!

# Redis
REDIS_PASSWORD=VotreAutreRedisPassword456!

# API
API_HOST=0.0.0.0
API_PORT=8000
API_HMAC_SECRET=VotreAutreSecretHMAC789!

# Scraping (AVEC proxies)
PROXY_ENABLED=true
PROXY_POOL=["http://user-country-fr:VOTRE_PASSWORD@gate.smartproxy.com:7000"]

# SmartProxy credentials
SMARTPROXY_USERNAME=user-country-fr
SMARTPROXY_PASSWORD=VotreSmartProxyPassword

# Rate limiting (plus conservateur pour Google)
DOWNLOAD_DELAY=5.0
CONCURRENT_REQUESTS=4
CONCURRENT_REQUESTS_PER_DOMAIN=1

# Smart throttle
SMART_THROTTLE_MIN_DELAY=2.0
SMART_THROTTLE_MAX_DELAY=60.0

# SerpAPI (optionnel)
SERPAPI_KEY=VotreCléSerpAPIOptionnelle

# Monitoring
LOG_LEVEL=INFO
PROMETHEUS_RETENTION=30d
```

### Configuration Proxies

```json
// config/proxy_config.json
{
  "providers": [
    {
      "name": "smartproxy",
      "type": "residential",
      "enabled": true,
      "proxies": [
        "http://user-country-fr:PASSWORD@gate.smartproxy.com:7000",
        "http://user-country-de:PASSWORD@gate.smartproxy.com:7000",
        "http://user-country-es:PASSWORD@gate.smartproxy.com:7000"
      ],
      "rotation": "auto",
      "health_check_url": "https://www.google.com",
      "max_failures": 5,
      "cooldown_seconds": 300
    }
  ],
  "fallback": {
    "enabled": true,
    "serpapi_enabled": false
  }
}
```

### Commandes de déploiement

```bash
# 1. SSH vers VPS 2
ssh root@88.198.45.123

# 2. Installation
cd /opt
git clone https://github.com/VOTRE-USERNAME/scraper-pro.git scraper-google
cd scraper-google

# 3. Configuration
cp .env.example .env
nano .env  # Remplir les valeurs + proxies

# 4. Configurer proxies
nano config/proxy_config.json  # Ajouter credentials SmartProxy

# 5. Utiliser docker-compose complet
cp docker-compose-google.yml docker-compose.yml

# 6. Démarrer
docker compose up -d

# 7. Vérifier
docker compose ps
curl http://localhost:8000/health

# 8. Accéder Grafana
# http://88.198.45.123:3001
# Login: admin / admin (changer au premier login)
```

### API Endpoints

```bash
# Base URL
http://88.198.45.123:8000

# Créer job Google Search
curl -X POST http://88.198.45.123:8000/api/v1/scraping/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "google_search",
    "query": "expat services paris",
    "max_results": 100,
    "country": "fr"
  }'

# Créer job Google Maps
curl -X POST http://88.198.45.123:8000/api/v1/scraping/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "google_maps",
    "query": "restaurants Paris",
    "max_results": 500
  }'

# Dashboard Streamlit
http://88.198.45.123:3000

# Grafana (monitoring)
http://88.198.45.123:3001
```

### Monitoring

**Grafana Dashboards :**
- http://88.198.45.123:3001
- Login : admin / admin
- Dashboards :
  - Scraper Overview
  - Proxy Performance
  - System Metrics

**Alertes configurées :**
- ScraperAPIDown → email
- HighJobFailureRate > 50% → email
- ProxyFailureRate > 30% → email
- HighMemoryUsage > 90% → email

---

## 🔄 CENTRALISATION DES DONNÉES (Optionnel)

Si vous voulez fusionner les contacts des 2 systèmes :

### Option 1 : Export/Import manuel

```bash
# Sur VPS 1 (URLs)
docker exec postgres pg_dump scraper_urls > urls_contacts.sql

# Transférer vers VPS 2
scp urls_contacts.sql root@88.198.45.123:/tmp/

# Sur VPS 2 (Google)
docker exec -i postgres psql scraper_google < /tmp/urls_contacts.sql
```

### Option 2 : Réplication PostgreSQL

Configurer réplication master-slave entre les 2 VPS (avancé).

### Option 3 : API de synchronisation

Créer endpoint API pour synchroniser contacts entre les 2 systèmes.

---

## 💰 COÛT TOTAL

| Item | Prix/mois | Prix/an |
|------|-----------|---------|
| VPS 1 (URLs) - CPX21 | 7.39€ | 88.68€ |
| VPS 2 (Google) - CPX31 | 11.90€ | 142.80€ |
| SmartProxy 8GB | 75€ | 900€ |
| **TOTAL** | **94.29€/mois** | **1,131.48€/an** |

---

## 📊 CAPACITÉS

### Système 1 (URLs)
- **30,000-50,000 URLs/jour**
- Stockage : millions de contacts
- Consommation proxy : **0 GB** ✅
- Taux de succès : 92-95%

### Système 2 (Google)
- **10,000-30,000 recherches/jour**
- Stockage : millions de contacts
- Consommation proxy : **~2-3 GB/jour** (60-90 GB/mois sur quota 8GB → upgrade si besoin)
- Taux de succès : 95-99%

---

## 🚀 ORDRE DE DÉPLOIEMENT

1. **Acheter VPS 1 (CPX21)** pour URLs
2. **Déployer système URLs** (2h)
3. **Tester scraping URLs** (expat.com, etc.)
4. **Acheter VPS 2 (CPX31)** pour Google
5. **Acheter SmartProxy 8GB**
6. **Déployer système Google** (3h)
7. **Tester scraping Google** avec proxies
8. **Configurer monitoring** sur système 2

**Total setup : 1-2 jours**

---

## ✅ AVANTAGES DE CETTE ARCHITECTURE

1. ✅ **Isolation complète** (2 IPs, 2 bases, zéro impact)
2. ✅ **Économie proxies** (URLs ne consomment rien)
3. ✅ **Sécurité** (blacklist Google isolée)
4. ✅ **Scalabilité indépendante**
5. ✅ **Monitoring ciblé** (lourd uniquement sur Google)

---

## 📞 SUPPORT

En cas de problème :
- Système URLs : Vérifier logs `docker compose logs -f`
- Système Google : Grafana → http://88.198.45.123:3001
- Proxies : Dashboard Streamlit onglet "Proxies"
