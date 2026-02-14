# 🚀 Configuration Dual-App Optimisée

## Vue Rapide

Ce package contient une **configuration Docker Compose optimisée** pour faire tourner **2 applications** sur un **seul serveur** (2 vCPU / 4 GB RAM) :

1. **Scraper-Pro** (scraping web + extraction de contacts)
2. **Backlink Engine** (votre outil de backlinks)

**Économie de RAM** : Les 2 apps partagent PostgreSQL et Redis → **~500 MB économisés** ✅

---

## 📦 Fichiers Créés

| Fichier | Description |
|---------|-------------|
| `docker-compose.optimized.yml` | Configuration Docker Compose pour 2 apps |
| `.env.optimized` | Template de configuration avec limites RAM |
| `scripts/postgres-init.sh` | Script d'initialisation PostgreSQL (2 bases) |
| `scripts/deploy-dual-app.sh` | Déploiement automatique complet |
| `docs/DUAL_APP_SETUP.md` | Documentation complète (installation, troubleshooting) |

---

## ⚡ Déploiement Rapide (5 minutes)

### Sur votre serveur Helsinki (2 vCPU / 4 GB RAM)

```bash
# 1. SSH vers le serveur
ssh root@VOTRE_IP_HELSINKI

# 2. Cloner le projet
cd /opt
git clone https://github.com/VOTRE-USERNAME/scraper-pro.git
cd scraper-pro

# 3. Rendre le script exécutable
chmod +x scripts/deploy-dual-app.sh
chmod +x scripts/postgres-init.sh

# 4. Lancer le déploiement automatique
./scripts/deploy-dual-app.sh

# ✅ C'est tout ! Le script fait TOUT automatiquement :
#    - Installe Docker/Docker Compose
#    - Génère tous les secrets (PostgreSQL, Redis, API, etc.)
#    - Crée les 2 bases de données (scraper_db, backlink_db)
#    - Démarre tous les services
#    - Applique les migrations
#    - Vérifie la santé des services
#    - Configure le firewall (optionnel)
```

**Temps total : ~5 minutes** ⏱️

---

## 🎯 Résultat

Après déploiement, vous aurez :

| Service | Port | URL | RAM |
|---------|------|-----|-----|
| **Scraper-Pro API** | 8000 | http://VOTRE_IP:8000 | ~400 MB |
| **Scraper-Pro Dashboard** | 8501 | http://VOTRE_IP:8501 | ~350 MB |
| **Scraper-Pro Worker** | - | (background) | ~700 MB |
| **Backlink Engine** | 8080 | http://VOTRE_IP:8080 | ~800 MB |
| **PostgreSQL** (partagé) | 5432 | (interne) | ~500 MB |
| **Redis** (partagé) | 6379 | (interne) | ~150 MB |
| **TOTAL** | - | - | **~2.9 GB / 4 GB** ✅ |

**Marge disponible : ~1.1 GB (27%)**

---

## 🔧 Configuration Backlink Engine

Le `docker-compose.optimized.yml` contient une section pour Backlink Engine **à adapter selon votre configuration** :

```yaml
backlink-engine:
  # ⚠️ Modifier selon votre image Docker
  image: your-backlink-engine:latest

  environment:
    # PostgreSQL (partagé)
    DB_HOST: postgres
    DB_DATABASE: backlink_db
    DB_USERNAME: shared_user
    DB_PASSWORD: ${POSTGRES_PASSWORD}

    # Redis (partagé, namespace 1)
    REDIS_HOST: redis
    REDIS_DB: 1

  ports:
    - "8080:80"  # ⚠️ Adapter selon votre port
```

**Si vous n'avez pas encore Backlink Engine**, commentez cette section et déployez uniquement Scraper-Pro.

---

## 📊 Commandes Utiles

### Vérifier l'état des services

```bash
# Liste des containers
docker compose -f docker-compose.optimized.yml ps

# Logs en temps réel
docker compose -f docker-compose.optimized.yml logs -f

# Logs d'un service spécifique
docker compose -f docker-compose.optimized.yml logs -f scraper-worker
```

### Monitoring RAM

```bash
# Vue instantanée
docker stats --no-stream

# Monitoring continu (rafraîchissement toutes les 5s)
watch -n 5 'docker stats --no-stream'

# RAM système
free -h
```

### Gestion des services

```bash
# Redémarrer un service
docker compose -f docker-compose.optimized.yml restart scraper-worker

# Arrêter tous les services
docker compose -f docker-compose.optimized.yml down

# Démarrer tous les services
docker compose -f docker-compose.optimized.yml up -d

# Reconstruire et redémarrer
docker compose -f docker-compose.optimized.yml up -d --build
```

### Accès aux bases de données

```bash
# Lister les bases de données
docker exec shared-postgres psql -U shared_user -c "\l"

# Se connecter à scraper_db
docker exec -it shared-postgres psql -U shared_user -d scraper_db

# Se connecter à backlink_db
docker exec -it shared-postgres psql -U shared_user -d backlink_db

# Vérifier Redis
docker exec shared-redis redis-cli -a $REDIS_PASSWORD ping
```

---

## 🚨 Si la RAM dépasse 90%

### Option 1 : Réduire la concurrence du scraper

```bash
nano .env

# Modifier :
CONCURRENT_REQUESTS=2  # Au lieu de 3
CONCURRENT_REQUESTS_PER_DOMAIN=1

# Redémarrer
docker compose -f docker-compose.optimized.yml restart scraper-worker
```

### Option 2 : Désactiver temporairement le Dashboard

```bash
# Stopper le Dashboard (économie : ~350 MB)
docker compose -f docker-compose.optimized.yml stop scraper-dashboard

# Redémarrer quand nécessaire
docker compose -f docker-compose.optimized.yml start scraper-dashboard
```

### Option 3 : Upgrade vers 8 GB RAM

**Sur Hetzner Cloud Console :**
1. Serveur → Resize → CPX31 (4 vCPU, 8 GB RAM, 11.90€/mois)
2. Après upgrade, augmenter `CONCURRENT_REQUESTS` à 6

---

## 📖 Documentation Complète

- **Installation détaillée** : [docs/DUAL_APP_SETUP.md](docs/DUAL_APP_SETUP.md)
- **Référence API** : [docs/API_QUICKSTART.md](docs/API_QUICKSTART.md)
- **Troubleshooting** : [docs/DUAL_APP_SETUP.md](docs/DUAL_APP_SETUP.md#-troubleshooting)
- **Monitoring** : [docs/DUAL_APP_SETUP.md](docs/DUAL_APP_SETUP.md#-monitoring-ram-en-continu)

---

## 🔐 Sécurité

Les secrets sont **générés automatiquement** par le script `deploy-dual-app.sh` et sauvegardés dans :

```
~/.scraper-secrets-YYYYMMDD_HHMMSS.txt
```

**⚠️ IMPORTANT** : Sauvegardez ce fichier dans un endroit sûr (gestionnaire de mots de passe, coffre-fort numérique).

---

## 💰 Coûts

| Configuration | Serveur | Proxies | Total/mois |
|---------------|---------|---------|------------|
| **Scraper-Pro + Backlink Engine (URLs)** | 5.99€ | 0€ | **5.99€** ✅ |
| **+ Google Search (futur)** | +11.90€ | +75€ | **92.89€** |
| **Upgrade vers 8 GB** | 11.90€ | 0€ | **11.90€** |

---

## 🆘 Support

**Problèmes fréquents** :

1. **PostgreSQL ne démarre pas** → Vérifier `chmod +x scripts/postgres-init.sh`
2. **RAM > 95%** → Réduire `CONCURRENT_REQUESTS` à 2
3. **Backlink Engine ne se connecte pas** → Vérifier les credentials dans `.env`

**Logs détaillés** : `docker compose -f docker-compose.optimized.yml logs -f`

---

## ✅ Checklist Rapide

- [ ] Script `deploy-dual-app.sh` exécuté
- [ ] Secrets sauvegardés (`~/.scraper-secrets-*.txt`)
- [ ] 2 bases créées (scraper_db, backlink_db)
- [ ] API Scraper-Pro : `curl http://localhost:8000/health` → OK
- [ ] Dashboard accessible : `http://VOTRE_IP:8501`
- [ ] RAM < 80% : `docker stats`
- [ ] Firewall configuré (optionnel)

---

**Votre configuration dual-app optimisée est prête ! 🎉**

**Premier test** :

```bash
# Créer un job de scraping (mode dev)
curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Test Expat",
    "config": {"urls": ["https://www.expat.com/fr/guide/"]},
    "max_results": 50
  }'

# Voir les logs
curl http://localhost:8000/api/v1/scraping/jobs/1/logs
```

**Bonne utilisation !** 🚀
