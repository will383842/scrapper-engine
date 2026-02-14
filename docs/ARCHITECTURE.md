# 🏗️ Architecture Technique - Scraper-Pro

Documentation complète de l'architecture du système **Scraper-Pro**.

---

## 📊 Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────────┐
│                        SCRAPER-PRO SYSTEM                        │
│                     (Microservices Architecture)                 │
└──────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   External   │         │   Frontend   │         │   Backend    │
│   Services   │◀───────▶│   Services   │◀───────▶│   Services   │
└──────────────┘         └──────────────┘         └──────────────┘
      │                         │                         │
      │                         │                         │
      ▼                         ▼                         ▼
┌─────────────┐         ┌──────────────┐        ┌───────────────┐
│  Oxylabs    │         │  Streamlit   │        │   FastAPI     │
│  BrightData │         │  Dashboard   │        │   REST API    │
│  SmartProxy │         │  (Port 8501) │        │  (Port 8000)  │
└─────────────┘         └──────────────┘        └───────────────┘
                                │                        │
                                └────────┬───────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────┐
                        │     Data Layer              │
                        ├─────────────────────────────┤
                        │  PostgreSQL 16 (Primary DB) │
                        │  Redis 7 (Cache + Queue)    │
                        └─────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────┐
                        │    Scrapy Engine            │
                        ├─────────────────────────────┤
                        │  4 Spiders (Google, Maps,   │
                        │  Custom URLs, Blog Content) │
                        └─────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────┐
                        │  Processing Pipeline        │
                        ├─────────────────────────────┤
                        │  Validation → Categorization│
                        │  → Routing → MailWizz Sync  │
                        └─────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────┐
                        │   External Integrations     │
                        ├─────────────────────────────┤
                        │  MailWizz API (SOS-Expat,   │
                        │  Ulixai) + Webhooks         │
                        └─────────────────────────────┘
```

---

## 🧩 Composants Principaux

### 1. **Scraper Service** (Container: `scraper-app`)

**Rôle** : Orchestrateur principal, API REST, exécution des spiders

**Technologies** :
- FastAPI 0.115 (Web framework)
- Uvicorn (ASGI server)
- Scrapy 2.11 (Scraping framework)
- SQLAlchemy 2.0 (ORM)
- Redis-py 5.2 (Cache client)

**Ports** :
- `8000` : API REST

**Endpoints principaux** :
```
GET  /health                              # Health check
POST /api/v1/scraping/jobs                # Créer un job
POST /api/v1/scraping/jobs/{id}/resume    # Reprendre un job
GET  /api/v1/scraping/jobs/{id}/status    # Statut du job
POST /api/v1/scraping/jobs/{id}/pause     # Pause un job
POST /api/v1/scraping/jobs/{id}/cancel    # Annuler un job
GET  /api/v1/contacts                     # Lister les contacts
POST /api/v1/whois/lookup                 # Lookup WHOIS
```

**Processus** :
```
1. API FastAPI (port 8000)
2. Cron daemon (process_contacts + sync_to_mailwizz)
3. Scrapy spiders (subprocess via runner.py)
```

---

### 2. **PostgreSQL 16** (Container: `scraper-postgres`)

**Rôle** : Base de données relationnelle principale

**Schéma** : 9 tables

| Table | Rôle | Taille estimée |
|-------|------|----------------|
| `scraping_jobs` | Jobs de scraping | ~1K rows |
| `scraped_contacts` | Contacts bruts | ~1M rows |
| `validated_contacts` | Contacts validés | ~500K rows |
| `mailwizz_sync_log` | Logs sync MailWizz | ~500K rows |
| `proxy_stats` | Stats proxies | ~100 rows |
| `url_fingerprints` | Cache anti-doublons | ~2M rows |
| `email_domain_blacklist` | Domaines blacklistés | ~1K rows |
| `error_logs` | Logs d'erreurs | ~10K rows |
| `whois_cache` | Cache WHOIS | ~100K rows |
| `scraped_articles` | Articles de blog | ~50K rows |

**Indexes** : 18 indexes (simples + composés)

**Connection Pool** :
- Pool size: 10
- Max overflow: 20
- Pre-ping: enabled

**Volumes** :
- `postgres_data:/var/lib/postgresql/data`

---

### 3. **Redis 7** (Container: `scraper-redis`)

**Rôle** : Cache, déduplication, queues

**Utilisation** :

```python
# Cache déduplication (par job)
scraper:seen_emails:{job_id} → SET [emails]

# Cache MX DNS lookup
scraper:mx_cache:{domain} → BOOLEAN

# Cache WHOIS (optionnel)
scraper:whois:{domain} → JSON
```

**Configuration** :
- Max memory: 512 MB (configurable)
- Eviction policy: `allkeys-lru`
- Persistence: RDB (snapshot)

---

### 4. **Scrapy Engine**

**Architecture** :

```
ScrapyEngine
├── Spiders (4)
│   ├── google_search_spider.py
│   ├── google_maps_spider.py
│   ├── generic_url_spider.py
│   └── blog_content_spider.py
├── Middlewares
│   ├── RandomUserAgentMiddleware
│   └── ProxyMiddleware
├── Pipelines
│   ├── DeduplicationPipeline (Redis)
│   ├── ValidationPipeline
│   ├── PostgresPipeline
│   ├── ArticlePipeline
│   └── ProgressTrackingPipeline
└── Items
    ├── ContactItem
    └── ArticleItem
```

**Flow d'un spider** :

```
1. start_requests()
   ├─ Charger checkpoint si resume=true
   ├─ Générer URLs à scraper
   └─ yield scrapy.Request()

2. parse() / parse_detail()
   ├─ Extraire données (XPath/CSS selectors)
   ├─ Yield ContactItem ou ArticleItem
   └─ Sauvegarder checkpoint

3. Pipelines
   ├─ DeduplicationPipeline : Drop si duplicate
   ├─ ValidationPipeline : Drop si invalide
   ├─ PostgresPipeline : Insert dans DB
   └─ ProgressTrackingPipeline : Update job stats

4. Fin
   └─ Update job status (completed/failed)
```

---

### 5. **Dashboard Streamlit** (Container: `scraper-dashboard`)

**Rôle** : Interface d'administration web

**Pages** :

```
Dashboard (app.py)
├── Tab 1: Jobs
│   ├── Liste des jobs (statut, progrès)
│   ├── Créer un nouveau job
│   └── Actions (resume, pause, cancel)
├── Tab 2: Contacts
│   ├── Stats (scraped, validated, sent)
│   ├── Recherche et filtres
│   ├── Détails contact
│   └── Export CSV
├── Tab 3: Articles
│   ├── Liste des articles
│   ├── Filtres (domain, langue)
│   ├── Détails article
│   └── Export CSV/JSON
├── Tab 4: Stats
│   ├── Volume scraping (30j)
│   ├── Sync MailWizz (30j)
│   ├── Domain blacklist
│   └── WHOIS stats
├── Tab 5: WHOIS Lookup
│   ├── Recherche manuelle
│   └─ Historique lookups
└── Tab 6: Configuration
    ├── System health
    ├── Proxy provider
    └── MailWizz routing
```

**Authentification** :
- Password-based (HMAC compare)
- Session state Streamlit

**Port** : `8501`

---

### 6. **Monitoring Stack**

#### Prometheus (Container: `scraper-prometheus`)

**Rôle** : Collecte et stockage des métriques

**Métriques exposées** :

```python
# FastAPI métriques (via prometheus-client)
scraper_requests_total                    # Total requests
scraper_requests_duration_seconds         # Request latency
scraper_jobs_running                      # Jobs en cours
scraper_jobs_completed_total              # Jobs terminés
scraper_contacts_scraped_total            # Contacts scrapés
scraper_contacts_validated_total          # Contacts validés
scraper_mailwizz_sync_success_total       # Sync réussis
scraper_mailwizz_sync_failed_total        # Sync échoués
scraper_proxy_requests_total              # Requêtes proxy
scraper_proxy_failures_total              # Échecs proxy
```

**Scrape config** :
```yaml
scrape_configs:
  - job_name: 'scraper-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['scraper:8000']
```

**Port** : `9090`

#### Grafana (Container: `scraper-grafana`)

**Rôle** : Visualisation des métriques

**Dashboards** :
1. **Scraper Overview** : Vue d'ensemble du système
2. **Jobs Monitoring** : Suivi des jobs de scraping
3. **MailWizz Sync** : Performance de la sync
4. **Proxies Health** : Santé des proxies
5. **Database Performance** : PostgreSQL metrics

**Port** : `3000`

#### Loki + Promtail (Containers: `scraper-loki`, `scraper-promtail`)

**Rôle** : Centralisation des logs

**Sources** :
- `/app/logs/*.log` (scraper)
- Docker container logs (stdout/stderr)

**Port** : `3100`

---

## 🔄 Pipeline de traitement

### Phase 1 : Scraping

```
┌─────────────┐
│ API Request │
│  (create    │
│   job)      │
└──────┬──────┘
       │
       v
┌─────────────┐
│ Insert into │
│ scraping_   │
│ jobs        │
└──────┬──────┘
       │
       v
┌─────────────┐
│ run_spider()│
│ (subprocess)│
└──────┬──────┘
       │
       ├──> Spider start_requests()
       │    │
       │    ├──> Proxy rotation
       │    ├──> User-agent rotation
       │    └──> Rate limiting
       │
       ├──> Parse pages
       │    │
       │    ├──> Extract emails
       │    ├──> Extract phones
       │    ├──> Extract social media
       │    └──> Extract WHOIS
       │
       ├──> Pipelines
       │    │
       │    ├──> DeduplicationPipeline
       │    ├──> ValidationPipeline
       │    └──> PostgresPipeline
       │
       └──> Insert into scraped_contacts
            (status: pending_validation)
```

### Phase 2 : Validation (Cron job - toutes les heures)

```
process_contacts.py
│
├──> SELECT * FROM scraped_contacts
│    WHERE status = 'pending_validation'
│    LIMIT 1000 FOR UPDATE SKIP LOCKED
│
├──> Pour chaque contact :
│    │
│    ├──> validate_email(email)
│    │    ├─ Regex check
│    │    ├─ MX DNS lookup (cached)
│    │    ├─ Blacklist prefixes
│    │    └─ Disposable domains check
│    │
│    ├──> Check duplicate in validated_contacts
│    │
│    ├──> Check domain blacklist (bounce rate > 10%)
│    │
│    ├──> categorize(contact)
│    │    ├─ Keywords scoring
│    │    ├─ Source type scoring
│    │    └─ Return best category
│    │
│    ├──> determine_platform(category)
│    │    ├─ SOS_EXPAT_CATEGORIES → "sos-expat"
│    │    └─ ULIXAI_CATEGORIES → "ulixai"
│    │
│    ├──> get_routing_info(category, platform)
│    │    └─ Return {list_id, template, tags}
│    │
│    └──> INSERT INTO validated_contacts
│         (status: ready_for_mailwizz)
│
└──> UPDATE scraped_contacts
     SET status = 'validated'
```

### Phase 3 : Sync MailWizz (Cron job - toutes les heures, +30min)

```
sync_to_mailwizz.py
│
├──> Check warmup quota (optionnel)
│    └─ get_daily_quota_remaining()
│
├──> SELECT * FROM validated_contacts
│    WHERE status = 'ready_for_mailwizz'
│    AND retry_count < 3
│    LIMIT min(100, quota_remaining)
│    FOR UPDATE SKIP LOCKED
│
├──> Pour chaque contact :
│    │
│    ├──> Build subscriber_data
│    │    ├─ EMAIL, FNAME, LNAME
│    │    ├─ COUNTRY, PHONE, WEBSITE
│    │    ├─ CATEGORY, SOURCE
│    │    └─ Social media fields
│    │
│    ├──> client.add_subscriber(list_id, data, tags)
│    │    │
│    │    ├─ HTTP POST to MailWizz API
│    │    └─ Return {success, subscriber_uid, error}
│    │
│    ├──> If success :
│    │    ├─ UPDATE validated_contacts
│    │    │   SET status = 'sent_to_mailwizz',
│    │    │       mailwizz_subscriber_id = uid
│    │    └─ INSERT INTO mailwizz_sync_log
│    │        (status: success)
│    │
│    └──> If error :
│         ├─ UPDATE validated_contacts
│         │   SET retry_count = retry_count + 1
│         │   SET last_error = error_msg
│         │   SET status = 'failed' IF retry_count >= 3
│         └─ INSERT INTO mailwizz_sync_log
│             (status: failed)
│
└──> Return stats {success, failed, retries}
```

---

## 🔐 Sécurité

### Authentification API (HMAC-SHA256)

```python
# Client génère la signature
timestamp = str(int(time.time()))
body = json.dumps(payload)
message = f"{timestamp}.{body}"
signature = hmac.sha256(API_HMAC_SECRET, message).hexdigest()

# Headers
X-Timestamp: 1707832800
X-Signature: a1b2c3d4e5f6...

# Serveur vérifie
if abs(time.time() - int(timestamp)) > 300:
    return 401  # Expired (5 min TTL)

expected_sig = hmac.sha256(API_HMAC_SECRET, message).hexdigest()
if not hmac.compare_digest(signature, expected_sig):
    return 401  # Invalid signature
```

### Network Isolation

```yaml
# docker-compose.yml
networks:
  scraper-network:
    driver: bridge

# Tous les services sur ce réseau privé
# Seuls ports exposés : 127.0.0.1:XXXX (localhost uniquement)
```

### Secrets Management

```bash
# .env (gitignored)
API_HMAC_SECRET=...
POSTGRES_PASSWORD=...
REDIS_PASSWORD=...
MAILWIZZ_*_API_KEY=...
WEBHOOK_*_SECRET=...

# Rotation recommandée : 90 jours
```

---

## 📈 Performance & Scalabilité

### Optimisations Database

```sql
-- Indexes composés pour les requêtes fréquentes
CREATE INDEX idx_scraped_status_scraped_at
    ON scraped_contacts(status, scraped_at ASC);

CREATE INDEX idx_validated_status_retry_created
    ON validated_contacts(status, retry_count, created_at ASC);

-- Connection pooling
pool_size=10, max_overflow=20, pool_pre_ping=True
```

### Rate Limiting

```python
# config/proxy_config.json
{
  "rate_limiting": {
    "default_delay_seconds": 2.0,
    "per_domain_limits": {
      "google.com": 5.0,      # 5s entre chaque requête Google
      "maps.google.com": 5.0
    }
  }
}

# settings.py (Scrapy)
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 2.0
AUTOTHROTTLE_ENABLED = True
```

### Cache Strategy

```
┌────────────┐
│   Redis    │
├────────────┤
│ MX Cache   │  TTL: 7 days (emails domaines)
│ Email Seen │  TTL: 24h (dédup par job)
│ WHOIS      │  TTL: 30 days (domaines)
└────────────┘

┌────────────┐
│ PostgreSQL │
├────────────┤
│ URL FP     │  Permanent (dédup global)
│ WHOIS      │  Permanent (cache longue durée)
└────────────┘
```

### Horizontal Scaling

**Actuellement** : Monolithe (1 scraper container)

**Pour scaler** :
```yaml
# docker-compose.yml
services:
  scraper:
    deploy:
      replicas: 3  # 3 instances de scraper-app

  # Load balancer (Nginx)
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
```

**Limites** :
- PostgreSQL : Max 100 connections (pool_size * replicas < 100)
- Redis : Non limitant (milliers de connections)
- Proxies : Limité par quota provider

---

## 🔄 Flux de données

### Diagramme de séquence - Création d'un job

```
User/API → FastAPI → Database → ScrapyEngine → Proxy → Google → Database → MailWizz

1. POST /api/v1/scraping/jobs
   ├─ FastAPI valide payload
   ├─ Insert dans scraping_jobs (status: pending)
   └─ run_spider(job_id, source_type, config)

2. run_spider() lance subprocess
   ├─ scrapy crawl google_search -a job_id=123
   ├─ Spider.start_requests()
   │   ├─ Load checkpoint si resume=true
   │   └─ Generate Google URLs
   ├─ Middleware : Proxy rotation
   ├─ Middleware : User-agent rotation
   ├─ Parse Google results
   │   ├─ Extract result URLs
   │   └─ Follow to detail pages
   ├─ Parse detail pages
   │   ├─ Extract email/phone/social
   │   └─ Yield ContactItem
   └─ Pipelines
       ├─ DeduplicationPipeline (Redis check)
       ├─ ValidationPipeline (format check)
       ├─ PostgresPipeline (INSERT scraped_contacts)
       └─ ProgressTrackingPipeline (UPDATE job stats)

3. Cron: process_contacts (toutes les heures)
   ├─ Fetch pending_validation
   ├─ validate_email() + categorize()
   └─ INSERT validated_contacts

4. Cron: sync_to_mailwizz (+30min)
   ├─ Fetch ready_for_mailwizz
   ├─ POST to MailWizz API
   └─ UPDATE status sent_to_mailwizz
```

---

## 📊 Schéma de base de données

Voir `db/init.sql` pour le schéma complet.

**Relations** :

```
scraping_jobs (1) ──< (N) scraped_contacts
                            │
                            │ (1:1)
                            ▼
                      validated_contacts (1) ──< (N) mailwizz_sync_log
```

---

## 🧪 Testing Strategy

```
tests/
├── test_api.py              # API endpoints
├── test_validator.py        # Email/phone validation
├── test_categorizer.py      # Catégorisation
├── test_mailwizz_client.py  # Client MailWizz
├── test_spiders.py          # Spiders Scrapy
├── test_pipelines.py        # Pipelines
├── test_proxy_manager.py    # Proxy rotation
├── test_checkpoint.py       # Checkpoint/resume
└── ... (8 autres fichiers)

# Run tests
docker-compose exec scraper pytest --cov=scraper --cov-report=html
```

---

## 🚀 Déploiement

Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour :
- Stratégie de déploiement
- Configuration production
- Scaling horizontal
- Disaster recovery

---

**Besoin de clarifications ?** Consultez le code source ou contactez l'équipe technique.
