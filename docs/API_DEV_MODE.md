# 🛠️ Mode Dev API - Guide Complet

Guide pour utiliser l'API Scraper-Pro en mode développement sans authentification HMAC.

---

## 🎯 Pourquoi un Mode Dev ?

### Avant (v1.0)

```bash
# Créer un job nécessitait HMAC signature
TIMESTAMP=$(date +%s)
BODY='{"source_type":"google_search","name":"Test"}'
SIGNATURE=$(echo -n "${TIMESTAMP}.${BODY}" | openssl dgst -sha256 -hmac "${API_SECRET}")

curl -X POST http://localhost:8000/api/v1/scraping/jobs \
  -H "X-Timestamp: ${TIMESTAMP}" \
  -H "X-Signature: ${SIGNATURE}" \
  -d "${BODY}"
```

**Problèmes :**
- ❌ Configuration complexe pour débuter
- ❌ Scripts Bash/Python verbeux
- ❌ Friction pour tests rapides
- ❌ Difficulté pour démonstrations

### Maintenant (v1.1+)

```bash
# Mode dev : un seul curl suffit
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Test",
    "config": {"urls": ["https://example.com"]}
  }'
```

**Avantages :**
- ✅ Zero configuration
- ✅ Tests instantanés
- ✅ Documentation plus claire
- ✅ Onboarding simplifié

---

## 🔐 Sécurité du Mode Dev

### Protection Localhost-Only

Le mode dev est **strictement limité à localhost** :

```python
# Code de sécurité (scraper/api/routes/scraping.py)
client_host = request.client.host
if client_host not in ["127.0.0.1", "localhost", "::1"]:
    raise HTTPException(
        status_code=403,
        detail="Dev mode: accessible uniquement depuis localhost"
    )
```

### Test de sécurité

**❌ Depuis une machine distante (BLOQUÉ) :**
```bash
# Depuis 192.168.1.100
curl -X POST http://192.168.1.50:8000/api/v1/scraping/jobs/simple ...
# Réponse : 403 Forbidden
```

**✅ Depuis localhost (AUTORISÉ) :**
```bash
# Sur la machine hôte
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple ...
# Réponse : 200 OK
```

### En Production

**Mode Dev → Désactivé automatiquement**

Quand vous déployez derrière Nginx/reverse proxy, le mode dev reste sécurisé car `request.client.host` sera toujours l'IP du proxy (pas le client final).

**Pour accès API distant en prod :** Utilisez les endpoints HMAC classiques.

---

## 📡 Endpoints Mode Dev

### 1. Créer un Job

**Endpoint :** `POST /api/v1/scraping/jobs/simple`

**Pas d'authentification requise** (localhost uniquement)

**Body :**
```json
{
  "source_type": "custom_urls",
  "name": "Mon Job",
  "config": {"urls": ["https://example.com"]},
  "max_results": 100
}
```

**Réponse :**
```json
{
  "success": true,
  "job_id": 123,
  "status": "created",
  "message": "Job créé avec succès (dev mode)"
}
```

**Exemples complets :** Voir [API_QUICKSTART.md](API_QUICKSTART.md#exemples-par-type-de-source)

---

### 2. Status d'un Job

**Endpoint :** `GET /api/v1/scraping/jobs/{job_id}/status`

**Pas d'authentification requise**

**Exemple :**
```bash
curl http://localhost:8000/api/v1/scraping/jobs/123/status
```

**Réponse :**
```json
{
  "id": 123,
  "name": "Mon Job",
  "source_type": "custom_urls",
  "status": "running",
  "progress": 45.50,
  "pages_scraped": 45,
  "contacts_extracted": 12,
  "errors_count": 2,
  "created_at": "2026-02-13T10:00:00Z",
  "started_at": "2026-02-13T10:00:05Z",
  "completed_at": null
}
```

---

### 3. Logs d'un Job

**Endpoint :** `GET /api/v1/scraping/jobs/{job_id}/logs`

**Pas d'authentification requise**

**Paramètres optionnels :**
- `limit` : Nombre max de logs (défaut: 100)
- `error_type` : Filtrer par type d'erreur

**Exemples :**
```bash
# Tous les logs
curl http://localhost:8000/api/v1/scraping/jobs/123/logs

# Filtrer par type
curl "http://localhost:8000/api/v1/scraping/jobs/123/logs?error_type=TimeoutError"

# Limiter les résultats
curl "http://localhost:8000/api/v1/scraping/jobs/123/logs?limit=50"
```

**Réponse :**
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
      "stack_trace": "Traceback..."
    }
  ],
  "count": 45,
  "has_errors": true
}
```

---

## 🎬 Workflows Pratiques

### Workflow 1 : Test Rapide

```bash
# 1. Créer job
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Quick Test",
    "config": {"urls": ["https://example.com"]}
  }'

# 2. Noter le job_id (ex: 123)

# 3. Status
curl http://localhost:8000/api/v1/scraping/jobs/123/status

# 4. Logs si erreur
curl http://localhost:8000/api/v1/scraping/jobs/123/logs
```

**Temps total :** ~2 minutes

---

### Workflow 2 : Monitoring Automatique

```bash
# Créer job + surveiller en une commande
JOB_ID=$(curl -s -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Auto Monitor Test",
    "config": {"urls": ["https://example.com"]}
  }' | jq -r '.job_id') \
&& ./scripts/monitor_job.sh $JOB_ID
```

**Résultat :** Job créé et surveillé automatiquement jusqu'à completion.

---

### Workflow 3 : Tests Parallèles

```bash
# Lancer plusieurs jobs en parallèle
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
    -H "Content-Type: application/json" \
    -d "{
      \"source_type\": \"custom_urls\",
      \"name\": \"Parallel Test $i\",
      \"config\": {\"urls\": [\"https://example$i.com\"]}
    }" &
done

# Attendre que tous finissent
wait

# Voir tous les jobs
curl http://localhost:8000/api/v1/scraping/jobs \
  -H "X-Signature: ..." | jq '.jobs[] | {id, name, status}'
```

**Use case :** Tests de performance, charge testing.

---

### Workflow 4 : CI/CD Integration

```yaml
# .github/workflows/test-scraper.yml
name: Test Scraper API

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Start Services
        run: docker-compose up -d

      - name: Wait for API
        run: |
          for i in {1..30}; do
            curl -f http://localhost:8000/health && break
            sleep 2
          done

      - name: Create Test Job
        run: |
          JOB_ID=$(curl -s -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
            -H "Content-Type: application/json" \
            -d '{
              "source_type": "custom_urls",
              "name": "CI Test",
              "config": {"urls": ["https://example.com"]}
            }' | jq -r '.job_id')
          echo "JOB_ID=$JOB_ID" >> $GITHUB_ENV

      - name: Wait for Completion
        run: |
          while true; do
            STATUS=$(curl -s http://localhost:8000/api/v1/scraping/jobs/$JOB_ID/status | jq -r '.status')
            echo "Job status: $STATUS"
            if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
              break
            fi
            sleep 10
          done

      - name: Check Results
        run: |
          CONTACTS=$(curl -s http://localhost:8000/api/v1/scraping/jobs/$JOB_ID/status | jq -r '.contacts_extracted')
          if [ "$CONTACTS" -lt 1 ]; then
            echo "ERROR: No contacts extracted"
            exit 1
          fi
```

---

## 🔄 Migration vers Production

### Phase de Dev (localhost)

```bash
# Mode dev : simple et rapide
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple ...
```

### Phase de Prod (serveur distant)

```bash
# Mode prod : HMAC requis
curl -X POST https://api.example.com/api/v1/scraping/jobs \
  -H "X-Timestamp: ${TIMESTAMP}" \
  -H "X-Signature: ${SIGNATURE}" \
  -d "${BODY}"
```

**Script de migration :**

```python
import os

# Configuration
IS_DEV = os.getenv("ENV") == "development"
API_URL = "http://localhost:8000" if IS_DEV else "https://api.example.com"

def create_job(data):
    if IS_DEV:
        # Mode dev : endpoint simple
        return requests.post(
            f"{API_URL}/api/v1/scraping/jobs/simple",
            json=data
        )
    else:
        # Mode prod : HMAC requis
        timestamp = str(int(time.time()))
        body = json.dumps(data)
        signature = generate_hmac(timestamp, body)

        return requests.post(
            f"{API_URL}/api/v1/scraping/jobs",
            json=data,
            headers={
                "X-Timestamp": timestamp,
                "X-Signature": signature
            }
        )
```

---

## 📊 Comparaison Modes

| Critère | Mode Dev | Mode Prod (HMAC) |
|---------|----------|------------------|
| **Authentification** | ❌ Aucune | ✅ HMAC-SHA256 |
| **Accès** | Localhost uniquement | N'importe quelle IP |
| **Setup** | Zero config | Secret API requis |
| **Sécurité** | Moyenne (localhost) | Haute (signature) |
| **Use case** | Tests, dev local | Production, CI/CD distant |
| **Endpoints** | `/jobs/simple`, `/status`, `/logs` | Tous les endpoints API |

---

## 🐛 Troubleshooting

### Erreur : `403 Forbidden (dev mode)`

**Cause :** Requête pas depuis localhost

**Solution :**
```bash
# ❌ Mauvais
curl -X POST http://192.168.1.50:8000/api/v1/scraping/jobs/simple ...

# ✅ Correct
ssh user@192.168.1.50
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple ...
```

---

### Erreur : `400 Bad Request - Invalid source_type`

**Cause :** `source_type` non supporté

**Solution :** Utiliser un type valide :
```json
{
  "source_type": "custom_urls",  // ✅
  "source_type": "google_search", // ✅
  "source_type": "google_maps",   // ✅
  "source_type": "blog_content",  // ✅
  "source_type": "invalid_type"   // ❌ Erreur
}
```

---

### Pas de Contacts Extraits

**Diagnostic :**
```bash
# 1. Vérifier le status
curl http://localhost:8000/api/v1/scraping/jobs/123/status | jq '.contacts_extracted'

# 2. Consulter les logs
curl http://localhost:8000/api/v1/scraping/jobs/123/logs | jq '.logs[] | {error_type, error_message}'

# 3. Causes courantes :
#    - Site protégé (Cloudflare) → Activer proxies
#    - URLs invalides → Vérifier config
#    - Pas d'emails sur la page → Normal
```

---

## 📚 Ressources

- 📖 [API Quick Start](API_QUICKSTART.md) - Guide 5 minutes
- 📖 [API Reference](API.md) - Documentation complète
- 📖 [Architecture](ARCHITECTURE.md) - Structure technique
- 🆕 [Changelog API](../CHANGELOG_API.md) - Nouveautés v1.1

---

## 🎓 Exemples Avancés

Consultez le dossier `examples/` (à créer) pour :
- Scripts Python complets
- Intégration avec MailWizz
- Monitoring avancé avec Grafana
- CI/CD templates

---

**Mode Dev API - Documentation v1.1**
Mise à jour : 2026-02-13
