# 🆕 API Changelog - Scraper-Pro

Historique des modifications et améliorations de l'API.

---

## [1.1.0] - 2026-02-13

### 🚀 Nouveautés

#### 1. Mode Dev - Endpoint Simple Sans HMAC

**Endpoint :** `POST /api/v1/scraping/jobs/simple`

Nouveau endpoint pour créer des jobs de scraping **sans authentification HMAC**, idéal pour le développement et les tests locaux.

**Caractéristiques :**
- ✅ Pas de signature HMAC requise
- ✅ Accessible uniquement depuis localhost (sécurité)
- ✅ Syntaxe simplifiée (pas besoin de credentials)
- ✅ Support de tous les types de sources (custom_urls, google_search, google_maps, blog_content)

**Exemple :**
```bash
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Test Job",
    "config": {"urls": ["https://example.com"]},
    "max_results": 100
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

**Sécurité :**
- Restreint aux IPs localhost : `127.0.0.1`, `localhost`, `::1`
- Retourne `403 Forbidden` pour toute autre origine

**Documentation :** Voir [API_QUICKSTART.md](docs/API_QUICKSTART.md)

---

#### 2. Endpoint Logs Détaillés

**Endpoint :** `GET /api/v1/scraping/jobs/{job_id}/logs`

Nouveau endpoint pour consulter les logs détaillés d'un job, incluant toutes les erreurs avec stack traces.

**Caractéristiques :**
- ✅ Pas d'authentification requise (dev mode)
- ✅ Filtrage par type d'erreur
- ✅ Limite configurable (défaut: 100)
- ✅ Timestamps précis
- ✅ Stack traces complètes pour debug

**Exemple :**
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
      "stack_trace": "Traceback (most recent call last):\n..."
    }
  ],
  "count": 45,
  "has_errors": true
}
```

**Types d'erreurs supportés :**
- `ConnectionError` : Échec de connexion
- `TimeoutError` : Timeout dépassé
- `HTTPError` : Erreurs HTTP (403, 404, 500, etc.)
- `ParseError` : Échec d'extraction
- `ProxyError` : Problème de proxy

---

#### 3. Status Endpoint Sans Authentification

**Endpoint :** `GET /api/v1/scraping/jobs/{job_id}/status`

L'endpoint de status est maintenant accessible **sans authentification HMAC** pour faciliter le développement.

**Avant (v1.0) :**
```bash
# Nécessitait HMAC
curl http://localhost:8000/api/v1/scraping/jobs/123/status \
  -H "X-Timestamp: ..." \
  -H "X-Signature: ..."
```

**Maintenant (v1.1) :**
```bash
# Plus simple
curl http://localhost:8000/api/v1/scraping/jobs/123/status
```

**Note :** L'endpoint HMAC reste disponible pour la production via les autres endpoints.

---

### 📚 Documentation

#### Nouveaux Fichiers

1. **[API_QUICKSTART.md](docs/API_QUICKSTART.md)** (NOUVEAU)
   - Guide complet "Premier job en 5 minutes"
   - Exemples copy-paste pour chaque type de source
   - Scripts de monitoring automatique
   - Troubleshooting détaillé

2. **[API.md](docs/API.md)** (MISE À JOUR)
   - Section "Quick Examples" ajoutée
   - Temps estimés par type de scraping
   - Documentation des nouveaux endpoints
   - Section Troubleshooting enrichie

---

### 🛠️ Scripts Utilitaires

#### 1. Monitor Job (Bash)

**Fichier :** `scripts/monitor_job.sh`

Script de surveillance en temps réel avec barre de progression et couleurs.

**Usage :**
```bash
./scripts/monitor_job.sh 123
./scripts/monitor_job.sh 123 5  # Intervalle 5s
```

**Fonctionnalités :**
- Barre de progression visuelle
- Couleurs selon le status
- Détection automatique de fin
- Lien vers logs en cas d'erreur

---

#### 2. Monitor Job (Python)

**Fichier :** `scripts/monitor_job.py`

Script Python multi-plateforme avec affichage enrichi (Rich).

**Usage :**
```bash
python scripts/monitor_job.py 123
python scripts/monitor_job.py 123 --interval 5
python scripts/monitor_job.py 123 --api-url http://prod:8000
```

**Dépendances :**
```bash
pip install requests rich
```

**Fonctionnalités :**
- Tableau de bord interactif
- Multi-plateforme (Windows, Linux, Mac)
- Support API distante
- Résumé final automatique

---

### 🔧 Améliorations Techniques

#### Sécurité

- Validation de l'origine pour mode dev (localhost only)
- HTTP 403 pour accès non autorisés
- Pas de faille SSRF (Server-Side Request Forgery)

#### Performance

- Pas d'impact sur les endpoints HMAC existants
- Query optimisées avec indexes PostgreSQL existants
- Pas de dépendances supplémentaires

#### Compatibilité

- ✅ Rétrocompatible à 100%
- ✅ Endpoints HMAC inchangés
- ✅ Schéma PostgreSQL inchangé
- ✅ Pas de migration requise

---

## Migration depuis v1.0

### Action Requise

**Aucune action requise !** 🎉

Tous les changements sont **additifs** et **rétrocompatibles**.

### Recommandations

1. **Développement :** Utilisez les nouveaux endpoints simples
   ```bash
   # Avant (v1.0)
   # Nécessitait HMAC pour tout

   # Maintenant (v1.1)
   curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple ...
   ```

2. **Production :** Continuez d'utiliser les endpoints HMAC
   ```bash
   # Toujours recommandé en production
   curl -X POST http://localhost:8000/api/v1/scraping/jobs \
     -H "X-Signature: ..."
   ```

3. **Monitoring :** Utilisez les scripts fournis
   ```bash
   ./scripts/monitor_job.sh <job_id>
   ```

---

## Prochaines Versions (Roadmap)

### [1.2.0] - Prévu Q2 2026

- [ ] Webhook pour notifications job terminé
- [ ] Export contacts en CSV via API
- [ ] Statistiques agrégées par période
- [ ] Endpoint batch pour créer plusieurs jobs

### [1.3.0] - Prévu Q3 2026

- [ ] API GraphQL (en plus de REST)
- [ ] WebSocket pour status temps réel
- [ ] Gestion fine des quotas par API key

---

## Support

**Questions ?**
- 📖 Consultez [API_QUICKSTART.md](docs/API_QUICKSTART.md)
- 📖 Consultez [API.md](docs/API.md)
- 🐛 Ouvrez une issue sur GitHub

**Contact :** Voir [README.md](README.md)

---

**Date de publication :** 2026-02-13
**Version API :** 1.1.0
**Compatibilité :** PostgreSQL 14+, Redis 6+, Python 3.11+
