# 🚀 API Quick Start - Premier Job en 5 Minutes

Guide rapide pour créer votre premier job de scraping avec Scraper-Pro.

---

## Prérequis

- Scraper-Pro installé et démarré (`docker-compose up -d`)
- `curl` ou Python installé
- API accessible sur `http://localhost:8000`

---

## Option A : Mode Simple (Dev - RECOMMANDÉ)

### 1. Health Check (30 secondes)

Vérifiez que l'API est opérationnelle :

```bash
curl http://localhost:8000/health
```

**Réponse attendue :**
```json
{
  "status": "ok",
  "service": "scraper-pro",
  "postgres": true,
  "redis": true
}
```

✅ Si `status: "ok"`, vous êtes prêt !

---

### 2. Créer Votre Premier Job (2 minutes)

#### Exemple 1 : Scraper des URLs personnalisées

```bash
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Mon Premier Job",
    "config": {
      "urls": ["https://www.expat.com/en/guide/"]
    },
    "max_results": 50
  }'
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

✅ **Notez le `job_id` (123 dans cet exemple)** - vous en aurez besoin pour suivre le job !

---

### 3. Vérifier le Status (1 minute)

Remplacez `123` par votre `job_id` :

```bash
JOB_ID=123  # Remplacer par le job_id obtenu

curl http://localhost:8000/api/v1/scraping/jobs/$JOB_ID/status
```

**Réponse :**
```json
{
  "id": 123,
  "name": "Mon Premier Job",
  "source_type": "custom_urls",
  "status": "running",
  "progress": 45.50,
  "pages_scraped": 23,
  "contacts_extracted": 12,
  "errors_count": 0,
  "created_at": "2026-02-13T10:00:00Z",
  "started_at": "2026-02-13T10:00:05Z",
  "completed_at": null
}
```

**Status possibles :**
- `pending` : En attente de démarrage
- `running` : Scraping en cours
- `completed` : Terminé avec succès
- `failed` : Échec (consultez les logs)
- `paused` : En pause
- `cancelled` : Annulé

---

### 4. Voir les Logs (1 minute)

Si vous rencontrez des erreurs ou voulez voir le détail :

```bash
curl http://localhost:8000/api/v1/scraping/jobs/$JOB_ID/logs
```

**Réponse :**
```json
{
  "job_id": 123,
  "job_name": "Mon Premier Job",
  "job_status": "running",
  "logs": [
    {
      "id": 1,
      "timestamp": "2026-02-13T10:05:23Z",
      "error_type": "TimeoutError",
      "error_message": "Request timeout after 30s",
      "url": "https://slow-site.com",
      "proxy_used": "http://proxy.example.com:8080",
      "stack_trace": "..."
    }
  ],
  "count": 1,
  "has_errors": true
}
```

Filtrer par type d'erreur :
```bash
curl "http://localhost:8000/api/v1/scraping/jobs/$JOB_ID/logs?error_type=TimeoutError"
```

---

### 🎉 Félicitations !

**TOTAL : ~5 MINUTES** ✅

Vous avez créé, suivi et débogué votre premier job de scraping !

---

## Option B : Mode Production (HMAC)

Pour la production, utilisez l'authentification HMAC (voir [API.md](API.md) pour les détails).

**Script Python avec HMAC :**

```python
import hashlib
import hmac
import json
import requests
import time

API_URL = "http://localhost:8000"
API_SECRET = "your_api_hmac_secret"  # Depuis .env

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
        "country": "fr"
    }
})

print(f"Job créé : #{job['job_id']}")
```

---

## Exemples par Type de Source

### 1. Scraper un Annuaire d'Avocats

```bash
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Annuaire Avocats Paris",
    "config": {
      "urls": ["https://www.annuaire-avocats.fr/avocats-paris/"]
    },
    "max_results": 500
  }'
```

**Temps estimé :** 15-30 minutes pour 500 profils

---

### 2. Recherche Google Search

```bash
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "google_search",
    "name": "Avocats Internationaux Paris",
    "config": {
      "query": "avocat droit international Paris",
      "max_results": 100,
      "country": "fr",
      "language": "fr"
    }
  }'
```

**Temps estimé :** 5-10 minutes pour 100 résultats

---

### 3. Google Maps (POI)

```bash
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "google_maps",
    "name": "Cabinets Avocats Paris",
    "config": {
      "query": "avocat",
      "location": "Paris, France",
      "max_results": 50,
      "language": "fr"
    }
  }'
```

**Temps estimé :** 10-15 minutes pour 50 POI

---

### 4. Scraper des Articles de Blog

```bash
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "blog_content",
    "name": "Articles Expat.com",
    "config": {
      "start_url": "https://www.expat.com/fr/guide/",
      "max_articles": 100,
      "scrape_depth": 2
    }
  }'
```

**Temps estimé :** 20-40 minutes pour 100 articles

---

## Script de Monitoring Automatique

Scraper-Pro inclut des scripts prêts à l'emploi pour surveiller vos jobs en temps réel.

### Option 1 : Script Bash (Linux/Mac/WSL)

```bash
# Se placer dans le dossier scripts
cd scripts

# Rendre exécutable
chmod +x monitor_job.sh

# Lancer la surveillance
./monitor_job.sh 123

# Avec intervalle personnalisé (5 secondes)
./monitor_job.sh 123 5
```

**Fonctionnalités :**
- ✅ Affichage en temps réel (status, progress, contacts)
- ✅ Barre de progression visuelle
- ✅ Détection automatique de fin de job
- ✅ Lien vers les logs en cas d'erreur
- ✅ Couleurs (si terminal compatible)

---

### Option 2 : Script Python (Multi-plateforme)

```bash
# Installer les dépendances (optionnelles, pour affichage enrichi)
pip install requests rich

# Lancer la surveillance
python scripts/monitor_job.py 123

# Avec intervalle personnalisé
python scripts/monitor_job.py 123 --interval 5

# API distante
python scripts/monitor_job.py 123 --api-url http://prod-server:8000
```

**Fonctionnalités :**
- ✅ Affichage enrichi avec Rich (si installé)
- ✅ Tableau de bord interactif
- ✅ Multi-plateforme (Windows, Linux, Mac)
- ✅ Support API distante
- ✅ Résumé final automatique

---

### Option 3 : Curl + Watch (Quick & Dirty)

```bash
# Linux/Mac
watch -n 10 "curl -s http://localhost:8000/api/v1/scraping/jobs/123/status | jq"

# Windows PowerShell
while ($true) {
  curl http://localhost:8000/api/v1/scraping/jobs/123/status | ConvertFrom-Json | Format-List
  Start-Sleep -Seconds 10
}
```

---

## Troubleshooting

| Erreur | Cause | Solution |
|--------|-------|----------|
| **403 Forbidden (dev mode)** | Pas depuis localhost | Utiliser `127.0.0.1` ou `localhost` (pas IP externe) |
| **400 Bad Request** | JSON invalide | Vérifier syntaxe JSON avec `jq` |
| **503 Service Unavailable** | API pas démarrée | `docker-compose up -d` |
| **Job status "failed"** | URLs invalides ou bloquées | Vérifier endpoint `/logs` |
| **"postgres": false** | PostgreSQL down | `docker-compose restart postgres` |
| **"redis": false** | Redis down | `docker-compose restart redis` |
| **Aucun contact extrait** | Site protégé (Cloudflare) | Activer proxies dans config |

---

## Prochaines Étapes

1. ✅ **Tester avec vos propres URLs** - Adaptez les exemples ci-dessus
2. ✅ **Consulter [API.md](API.md)** pour fonctionnalités avancées :
   - Pause/Resume de jobs
   - Gestion des contacts validés
   - Webhooks MailWizz
   - WHOIS lookup
3. ✅ **Configurer MailWizz** pour sync automatique des contacts
4. ✅ **Activer Grafana** pour monitoring visuel (`http://localhost:3000`)
5. ✅ **Explorer le Dashboard** Streamlit (`http://localhost:8501`)

---

## Ressources Complémentaires

- 📖 [API Reference complète](API.md)
- 🏗️ [Architecture du système](ARCHITECTURE.md)
- 🚀 [Guide de déploiement](DEPLOYMENT.md)
- 🔧 [Configuration avancée](../README.md)

---

**Questions ?** Consultez les logs avec l'endpoint `/logs` ou ouvrez une issue sur GitHub.

**Temps de lecture :** 8 minutes | **Temps de mise en pratique :** 5 minutes
