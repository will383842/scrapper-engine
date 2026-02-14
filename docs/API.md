# 🔌 API Reference - Scraper-Pro

Documentation complète de l'API REST **Scraper-Pro**.

**Base URL** : `http://localhost:8000`

---

## 🚀 Quick Examples

### Mode Simple (Dev - Sans HMAC)

Pour débuter rapidement sans configuration HMAC :

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Créer un job
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Test Job",
    "config": {"urls": ["https://example.com"]},
    "max_results": 50
  }'

# 3. Vérifier le status (remplacer 123 par le job_id obtenu)
curl http://localhost:8000/api/v1/scraping/jobs/123/status

# 4. Voir les logs en cas d'erreur
curl http://localhost:8000/api/v1/scraping/jobs/123/logs
```

**⚠️ Mode Dev uniquement** : accessible uniquement depuis `localhost` (127.0.0.1, ::1)

📖 **Guide complet** : [API_QUICKSTART.md](API_QUICKSTART.md) - Premier job en 5 minutes

---

### Temps Estimés par Type de Scraping

| Type | Nombre | Temps Estimé | Notes |
|------|--------|--------------|-------|
| **custom_urls** | 50 URLs | 5-10 min | Dépend de la vitesse des sites |
| **custom_urls** | 500 URLs | 30-60 min | Utiliser proxies recommandé |
| **google_search** | 100 résultats | 5-10 min | ~10 résultats/page |
| **google_maps** | 50 POI | 10-15 min | Avec détails complets |
| **blog_content** | 100 articles | 15-30 min | Profondeur 2 niveaux |

💡 **Astuce** : Surveillez `progress` et `contacts_extracted` via `/status` pour suivre l'avancement.

---

## 🔐 Authentification

Toutes les routes (sauf `/health`) requièrent une authentification **HMAC-SHA256**.

### Génération de la signature

```python
import hashlib
import hmac
import json
import time

# Configuration
API_HMAC_SECRET = "votre_secret_hmac"
timestamp = str(int(time.time()))
payload = {"source_type": "google_search", "name": "Test"}
body = json.dumps(payload)

# Générer la signature
message = f"{timestamp}.{body}"
signature = hmac.new(
    API_HMAC_SECRET.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

# Headers
headers = {
    "Content-Type": "application/json",
    "X-Timestamp": timestamp,
    "X-Signature": signature
}
```

### Exemple cURL

```bash
#!/bin/bash
API_SECRET="your_api_hmac_secret"
TIMESTAMP=$(date +%s)
BODY='{"source_type":"google_search","name":"Test"}'
SIGNATURE=$(echo -n "${TIMESTAMP}.${BODY}" | openssl dgst -sha256 -hmac "${API_SECRET}" | awk '{print $2}')

curl -X POST http://localhost:8000/api/v1/scraping/jobs \
  -H "Content-Type: application/json" \
  -H "X-Timestamp: ${TIMESTAMP}" \
  -H "X-Signature: ${SIGNATURE}" \
  -d "${BODY}"
```

---

## 📋 Health Check

### `GET /health`

Vérifier la santé du système.

**Authentification** : ❌ Non requise

**Réponse** :

```json
{
  "status": "ok",  // ou "degraded"
  "service": "scraper-pro",
  "postgres": true,
  "redis": true
}
```

**Codes HTTP** :
- `200 OK` : Tous les services sont opérationnels
- `503 Service Unavailable` : Au moins un service down

---

## 🕷️ Scraping Jobs

### `POST /api/v1/scraping/jobs/simple`

**🆕 NOUVEAU** - Créer un job de scraping SANS authentification HMAC (dev mode).

**Authentification** : ❌ Non requise (localhost uniquement)

**Body** :

```json
{
  "source_type": "custom_urls",
  "name": "Mon Job",
  "config": {
    "urls": ["https://example.com"]
  },
  "max_results": 100
}
```

**Réponse** :

```json
{
  "success": true,
  "job_id": 123,
  "status": "created",
  "message": "Job créé avec succès (dev mode)"
}
```

**Exemples de configurations** : Voir [API_QUICKSTART.md](API_QUICKSTART.md)

**Codes HTTP** :
- `200 OK` : Job créé et démarré
- `400 Bad Request` : Payload invalide
- `403 Forbidden` : Requête pas depuis localhost

---

### `POST /api/v1/scraping/jobs`

Créer un nouveau job de scraping (mode production avec HMAC).

**Authentification** : ✅ HMAC requis

**Body** :

```json
{
  "source_type": "google_search",  // ou "google_maps", "custom_urls", "blog_content"
  "name": "Avocats Paris",
  "config": {
    // Config spécifique au source_type (voir ci-dessous)
  },
  "category": "avocat",  // optionnel, null = auto-detect
  "platform": "sos-expat",  // optionnel, null = auto-detect
  "tags": ["test", "paris"],  // optionnel
  "auto_inject_mailwizz": true  // optionnel, défaut: true
}
```

#### Config pour `google_search`

```json
{
  "query": "avocat international Paris",
  "max_results": 100,
  "country": "fr",  // optionnel: fr, us, uk, de, etc.
  "language": "fr"  // optionnel: fr, en, es, etc.
}
```

#### Config pour `google_maps`

```json
{
  "query": "avocat",
  "location": "Paris, France",
  "max_results": 50,
  "language": "fr"  // optionnel
}
```

#### Config pour `custom_urls`

```json
{
  "urls": [
    "https://example.com",
    "https://another-site.com/contact"
  ]
}
```

#### Config pour `blog_content`

```json
{
  "start_url": "https://www.expat.com/blog/",
  "max_articles": 100,
  "scrape_depth": 2  // niveaux de profondeur
}
```

**Réponse** :

```json
{
  "job_id": 123,
  "status": "created"
}
```

**Codes HTTP** :
- `200 OK` : Job créé et démarré
- `400 Bad Request` : Payload invalide
- `401 Unauthorized` : HMAC invalide

---

### `GET /api/v1/scraping/jobs/{job_id}/status`

Obtenir le statut d'un job.

**Authentification** : ❌ Non requise (dev mode activé)

**Réponse** :

```json
{
  "id": 123,
  "name": "Avocats Paris",
  "source_type": "google_search",
  "status": "running",  // pending, running, paused, completed, failed
  "progress": 45.50,  // pourcentage
  "pages_scraped": 45,
  "contacts_extracted": 12,
  "errors_count": 2,
  "created_at": "2026-02-13T10:00:00Z",
  "started_at": "2026-02-13T10:00:05Z",
  "completed_at": null,
  "checkpoint_data": {
    "last_page": 45,
    "results_collected": 45
  },
  "resume_count": 0
}
```

**Codes HTTP** :
- `200 OK` : Job trouvé
- `404 Not Found` : Job inexistant

---

### `GET /api/v1/scraping/jobs/{job_id}/logs`

**🆕 NOUVEAU** - Récupère les logs détaillés d'un job (erreurs, warnings, etc.).

**Authentification** : ❌ Non requise (dev mode)

**Query Parameters** :

| Param | Type | Description | Défaut |
|-------|------|-------------|--------|
| `limit` | int | Nombre max de logs | 100 |
| `error_type` | string | Filtrer par type d'erreur | tous |

**Exemple** :

```bash
# Tous les logs
curl http://localhost:8000/api/v1/scraping/jobs/123/logs

# Filtrer par type
curl "http://localhost:8000/api/v1/scraping/jobs/123/logs?error_type=TimeoutError"

# Limiter les résultats
curl "http://localhost:8000/api/v1/scraping/jobs/123/logs?limit=50"
```

**Réponse** :

```json
{
  "job_id": 123,
  "job_name": "Mon Job",
  "job_status": "running",
  "logs": [
    {
      "id": 1,
      "timestamp": "2026-02-13T14:30:00Z",
      "error_type": "ConnectionError",
      "error_message": "Failed to connect to example.com",
      "url": "https://example.com",
      "proxy_used": "http://proxy.example.com:8080",
      "stack_trace": "Traceback (most recent call last):\n..."
    }
  ],
  "count": 45,
  "has_errors": true
}
```

**Types d'erreurs courants** :
- `ConnectionError` : Échec de connexion au site
- `TimeoutError` : Dépassement du délai d'attente
- `HTTPError` : Erreur HTTP (403, 404, 500, etc.)
- `ParseError` : Échec d'extraction des données
- `ProxyError` : Problème avec le proxy utilisé

**Codes HTTP** :
- `200 OK` : Logs récupérés (peut être vide si aucune erreur)
- `404 Not Found` : Job inexistant

💡 **Astuce** : Si `has_errors: true` et `job_status: "failed"`, consultez les logs pour diagnostiquer le problème.

---

### `POST /api/v1/scraping/jobs/{job_id}/resume`

Reprendre un job échoué ou en pause depuis son dernier checkpoint.

**Authentification** : ✅ HMAC requis

**Réponse** :

```json
{
  "job_id": 123,
  "status": "resuming",
  "resume_count": 1,
  "checkpoint": {
    "last_page": 45,
    "results_collected": 45
  }
}
```

**Codes HTTP** :
- `200 OK` : Job repris
- `400 Bad Request` : Status invalide (doit être `failed` ou `paused`)
- `404 Not Found` : Job inexistant

---

### `POST /api/v1/scraping/jobs/{job_id}/pause`

Mettre en pause un job en cours.

**Authentification** : ✅ HMAC requis

**Réponse** :

```json
{
  "job_id": 123,
  "status": "paused"
}
```

**Codes HTTP** :
- `200 OK` : Job mis en pause
- `400 Bad Request` : Status invalide (doit être `running`)
- `404 Not Found` : Job inexistant

⚠️ **Note** : Le spider finira la page en cours avant de s'arrêter.

---

### `POST /api/v1/scraping/jobs/{job_id}/cancel`

Annuler un job (arrêt permanent).

**Authentification** : ✅ HMAC requis

**Réponse** :

```json
{
  "job_id": 123,
  "status": "failed"
}
```

**Codes HTTP** :
- `200 OK` : Job annulé
- `404 Not Found` : Job inexistant

⚠️ **Note** : Un job annulé ne peut pas être repris.

---

## 👥 Contacts

### `GET /api/v1/contacts`

Lister les contacts validés (avec filtres).

**Authentification** : ✅ HMAC requis

**Query Parameters** :

| Param | Type | Description | Défaut |
|-------|------|-------------|--------|
| `status` | string | `ready_for_mailwizz`, `sent_to_mailwizz`, `failed`, `bounced` | tous |
| `platform` | string | `sos-expat`, `ulixai` | tous |
| `category` | string | `avocat`, `blogueur`, etc. | tous |
| `limit` | int | Nombre max de résultats | 100 |
| `offset` | int | Pagination | 0 |

**Exemple** :

```
GET /api/v1/contacts?status=sent_to_mailwizz&platform=sos-expat&limit=50
```

**Réponse** :

```json
{
  "total": 1234,
  "limit": 50,
  "offset": 0,
  "contacts": [
    {
      "id": 456,
      "email": "john.doe@example.com",
      "name": "John Doe",
      "phone": "+33612345678",
      "website": "https://example.com",
      "category": "avocat",
      "platform": "sos-expat",
      "country": "FR",
      "tags": ["avocat", "google_search", "2026-02"],
      "status": "sent_to_mailwizz",
      "mailwizz_list_id": 1,
      "mailwizz_subscriber_id": "abc123",
      "sent_to_mailwizz_at": "2026-02-13T12:00:00Z",
      "created_at": "2026-02-13T11:00:00Z"
    }
  ]
}
```

---

### `GET /api/v1/contacts/{contact_id}`

Obtenir le détail d'un contact.

**Authentification** : ✅ HMAC requis

**Réponse** :

```json
{
  "id": 456,
  "email": "john.doe@example.com",
  "name": "John Doe",
  "phone": "+33612345678",
  "website": "https://example.com",
  "address": "123 Rue Example, Paris",
  "social_media": {
    "facebook": "https://facebook.com/johndoe",
    "linkedin": "https://linkedin.com/in/johndoe"
  },
  "category": "avocat",
  "platform": "sos-expat",
  "country": "FR",
  "tags": ["avocat", "google_search", "2026-02"],
  "email_valid": true,
  "phone_valid": true,
  "last_validated_at": "2026-02-13T11:30:00Z",
  "mailwizz_list_id": 1,
  "mailwizz_template": "partenariat_avocat",
  "mailwizz_subscriber_id": "abc123",
  "status": "sent_to_mailwizz",
  "sent_to_mailwizz_at": "2026-02-13T12:00:00Z",
  "retry_count": 0,
  "last_error": null,
  "created_at": "2026-02-13T11:00:00Z",
  "updated_at": "2026-02-13T12:00:00Z"
}
```

**Codes HTTP** :
- `200 OK` : Contact trouvé
- `404 Not Found` : Contact inexistant

---

## 🌐 WHOIS Lookup

### `POST /api/v1/whois/lookup`

Effectuer un lookup WHOIS pour un domaine.

**Authentification** : ✅ HMAC requis

**Body** :

```json
{
  "domain": "example.com"
}
```

**Réponse** :

```json
{
  "domain": "example.com",
  "registrar": "GoDaddy.com, LLC",
  "registrar_url": "https://www.godaddy.com",
  "creation_date": "1995-08-14T00:00:00Z",
  "expiration_date": "2027-08-13T00:00:00Z",
  "updated_date": "2026-07-09T00:00:00Z",
  "whois_private": false,
  "cloudflare_protected": false,
  "registrant_name": "Registration Private",
  "registrant_org": "Domains By Proxy, LLC",
  "registrant_email": null,
  "registrant_country": "US",
  "name_servers": [
    "ns1.example.com",
    "ns2.example.com"
  ],
  "lookup_status": "success",
  "looked_up_at": "2026-02-13T14:00:00Z"
}
```

**Codes HTTP** :
- `200 OK` : Lookup réussi (même si WHOIS privé)
- `400 Bad Request` : Domaine invalide

⚠️ **Note** : Les résultats sont mis en cache (30 jours).

---

## 📊 Campaigns (MailWizz)

### `POST /api/v1/campaigns/create`

Créer une campagne MailWizz.

**Authentification** : ✅ HMAC requis

**Body** :

```json
{
  "platform": "sos-expat",  // ou "ulixai"
  "list_id": 1,
  "name": "Campagne Avocats Mars 2026",
  "subject": "Partenariat SOS-Expat",
  "template_id": "partenariat_avocat",
  "from_name": "SOS-Expat",
  "from_email": "contact@sos-expat.com",
  "reply_to": "contact@sos-expat.com",
  "send_at": "2026-03-01T09:00:00Z"  // optionnel, null = immédiat
}
```

**Réponse** :

```json
{
  "campaign_id": "abc123xyz",
  "status": "pending-sending",  // ou "draft" si send_at est défini
  "created_at": "2026-02-13T14:30:00Z"
}
```

**Codes HTTP** :
- `201 Created` : Campagne créée
- `400 Bad Request` : Payload invalide
- `503 Service Unavailable` : MailWizz API down

---

## 🔄 Webhooks (Callbacks)

Le système **reçoit** des webhooks de MailWizz pour les événements email.

### Endpoint interne : `POST /api/v1/webhooks/email-events`

**Authentification** : ✅ HMAC requis (secret : `WEBHOOK_*_SECRET`)

**Body** :

```json
{
  "event": "bounce",  // ou "open", "click", "unsubscribe"
  "email": "john.doe@example.com",
  "subscriber_uid": "abc123",
  "list_id": 1,
  "campaign_id": "xyz789",
  "timestamp": "2026-02-13T15:00:00Z",
  "bounce_type": "hard",  // si event=bounce
  "bounce_reason": "Mailbox does not exist"
}
```

**Actions automatiques** :

| Event | Action |
|-------|--------|
| `bounce` (hard) | 1. UPDATE validated_contacts SET status='bounced'<br>2. UPDATE email_domain_blacklist (increment bounce_count) |
| `open` | Log seulement (stats) |
| `click` | Log seulement (stats) |
| `unsubscribe` | UPDATE validated_contacts SET status='unsubscribed' |

**Réponse** :

```json
{
  "received": true
}
```

---

## 📈 Métriques (Prometheus)

### `GET /metrics`

Exposer les métriques Prometheus.

**Authentification** : ❌ Non requise

**Format** : Prometheus text format

**Exemple** :

```
# HELP scraper_jobs_running Number of running jobs
# TYPE scraper_jobs_running gauge
scraper_jobs_running 3

# HELP scraper_contacts_scraped_total Total contacts scraped
# TYPE scraper_contacts_scraped_total counter
scraper_contacts_scraped_total 12345

# HELP scraper_requests_total Total HTTP requests
# TYPE scraper_requests_total counter
scraper_requests_total{method="POST",endpoint="/api/v1/scraping/jobs",status="200"} 42
```

---

## ⚠️ Codes d'erreur

| Code | Signification | Action |
|------|---------------|--------|
| `200` | OK | Succès |
| `201` | Created | Ressource créée |
| `400` | Bad Request | Vérifier le payload |
| `401` | Unauthorized | Vérifier HMAC signature |
| `403` | Forbidden | Dev mode: requête pas depuis localhost |
| `404` | Not Found | Ressource inexistante |
| `429` | Too Many Requests | Rate limit dépassé, attendre |
| `500` | Internal Server Error | Erreur serveur, contacter admin |
| `503` | Service Unavailable | Service temporairement indisponible |

---

## 🔧 Troubleshooting

### Job Status "failed"

**Diagnostic :**
```bash
# 1. Récupérer les logs d'erreur
curl http://localhost:8000/api/v1/scraping/jobs/123/logs

# 2. Vérifier le status détaillé
curl http://localhost:8000/api/v1/scraping/jobs/123/status
```

**Causes courantes :**

| Error Type | Cause | Solution |
|------------|-------|----------|
| `ConnectionError` | Site down ou bloqué | Vérifier URL, activer proxies |
| `TimeoutError` | Site très lent | Augmenter timeout dans config |
| `HTTPError 403` | Cloudflare/WAF | Activer proxies résidentiels |
| `HTTPError 404` | URL invalide | Vérifier les URLs dans config |
| `ProxyError` | Proxy down | Changer de pool de proxies |
| `ParseError` | Structure HTML changée | Adapter les sélecteurs CSS |

---

### Aucun Contact Extrait

**Vérifications :**

1. **Le job est-il terminé ?**
   ```bash
   curl http://localhost:8000/api/v1/scraping/jobs/123/status | jq '.status'
   # Doit être "completed"
   ```

2. **Y a-t-il des erreurs ?**
   ```bash
   curl http://localhost:8000/api/v1/scraping/jobs/123/logs | jq '.count'
   # Si > 0, consultez les logs détaillés
   ```

3. **Les URLs sont-elles valides ?**
   - Tester manuellement dans un navigateur
   - Vérifier que le site contient des emails/téléphones

4. **Le site est-il protégé ?**
   ```bash
   curl -I https://target-site.com | grep -i cloudflare
   # Si présent, activer proxies
   ```

---

### Performance Lente

**Optimisations :**

1. **Activer les proxies** (parallélisation)
   ```json
   {
     "config": {
       "use_proxies": true,
       "concurrent_requests": 8
     }
   }
   ```

2. **Réduire le scrape_depth** pour blog_content
   ```json
   {
     "config": {
       "scrape_depth": 1  // au lieu de 2 ou 3
     }
   }
   ```

3. **Augmenter les workers Scrapy**
   ```bash
   # Dans docker-compose.yml
   environment:
     SCRAPY_CONCURRENT_REQUESTS: 16
   ```

---

### Mode Dev (localhost uniquement)

**Erreur : `403 Forbidden (dev mode)`**

❌ **Mauvais :**
```bash
# Depuis une machine distante
curl -X POST http://192.168.1.100:8000/api/v1/scraping/jobs/simple ...
```

✅ **Correct :**
```bash
# Directement sur la machine hôte
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple ...
# ou
curl -X POST http://127.0.0.1:8000/api/v1/scraping/jobs/simple ...
```

**Pour accès distant :** Utilisez l'endpoint HMAC `/api/v1/scraping/jobs` (voir section Authentification).

---

### Health Check Failed

**Diagnostic :**
```bash
curl http://localhost:8000/health
```

**Cas 1 : `"postgres": false`**
```bash
# Vérifier que PostgreSQL est démarré
docker-compose ps postgres

# Redémarrer si nécessaire
docker-compose restart postgres

# Vérifier les logs
docker-compose logs postgres --tail 50
```

**Cas 2 : `"redis": false`**
```bash
# Vérifier Redis
docker-compose ps redis

# Redémarrer
docker-compose restart redis

# Test manuel
redis-cli ping
# Doit retourner: PONG
```

**Cas 3 : `503 Service Unavailable`**
```bash
# L'API elle-même ne répond pas
docker-compose restart api

# Vérifier les logs
docker-compose logs api --tail 100
```

---

## 🧪 Exemples complets

### Créer un job Google Search

```python
import hashlib
import hmac
import json
import requests
import time

API_URL = "http://localhost:8000"
API_SECRET = "your_api_hmac_secret"

def make_request(method, path, data=None):
    timestamp = str(int(time.time()))
    body = json.dumps(data) if data else ""
    message = f"{timestamp}.{body}"
    signature = hmac.new(
        API_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Signature": signature
    }

    response = requests.request(
        method,
        f"{API_URL}{path}",
        headers=headers,
        json=data
    )
    return response.json()

# Créer un job
job = make_request("POST", "/api/v1/scraping/jobs", {
    "source_type": "google_search",
    "name": "Avocats Paris",
    "config": {
        "query": "avocat international Paris",
        "max_results": 100,
        "country": "fr",
        "language": "fr"
    },
    "category": "avocat",
    "platform": "sos-expat",
    "tags": ["test", "paris"],
    "auto_inject_mailwizz": True
})

print(f"Job created: #{job['job_id']}")

# Suivre le progrès
while True:
    status = make_request("GET", f"/api/v1/scraping/jobs/{job['job_id']}/status")
    print(f"Status: {status['status']} - Progress: {status['progress']}%")

    if status['status'] in ('completed', 'failed'):
        break

    time.sleep(10)

print(f"Job finished: {status['status']}")
print(f"Contacts extracted: {status['contacts_extracted']}")
```

---

## 📚 Ressources

- 🏗️ [Architecture](ARCHITECTURE.md)
- 📦 [Installation](INSTALLATION.md)
- 🚀 [Déploiement](DEPLOYMENT.md)

---

**Questions ?** Consultez le code source ou contactez l'équipe technique.
