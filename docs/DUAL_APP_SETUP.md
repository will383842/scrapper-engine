# 🚀 Configuration Dual-App Optimisée

## Vue d'ensemble

Ce guide explique comment déployer **Scraper-Pro** ET **Backlink Engine** sur le **même serveur** (2 vCPU / 4 GB RAM) en partageant les services (PostgreSQL + Redis) pour économiser la RAM.

---

## 📊 Architecture Optimisée

```
┌─────────────────────────────────────────────────────────┐
│  Serveur : 2 vCPU / 4 GB RAM / 80 GB Disk (5.99€/mois)  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────┐        │
│  │  SERVICES PARTAGÉS                          │        │
│  ├─────────────────────────────────────────────┤        │
│  │  📦 PostgreSQL (500 MB)                     │        │
│  │     ├─ scraper_db   → Scraper-Pro          │        │
│  │     └─ backlink_db  → Backlink Engine      │        │
│  │                                              │        │
│  │  📦 Redis (150 MB)                          │        │
│  │     ├─ Namespace 0  → Scraper-Pro          │        │
│  │     └─ Namespace 1  → Backlink Engine      │        │
│  └─────────────────────────────────────────────┘        │
│                                                           │
│  ┌─────────────────────────────────────────────┐        │
│  │  APPLICATION 1 : SCRAPER-PRO (1.45 GB)     │        │
│  ├─────────────────────────────────────────────┤        │
│  │  🔧 API (400 MB)        → Port 8000        │        │
│  │  ⚙️  Worker (700 MB)    → Background       │        │
│  │  📊 Dashboard (350 MB)  → Port 8501        │        │
│  └─────────────────────────────────────────────┘        │
│                                                           │
│  ┌─────────────────────────────────────────────┐        │
│  │  APPLICATION 2 : BACKLINK ENGINE (800 MB)  │        │
│  ├─────────────────────────────────────────────┤        │
│  │  🌐 App (800 MB)        → Port 8080        │        │
│  └─────────────────────────────────────────────┘        │
│                                                           │
│  Total RAM utilisée : ~2.7 GB / 4 GB (~67%)              │
│  Marge disponible : ~1.3 GB (33%)                        │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Avantages de cette Configuration

| Avantage | Description |
|----------|-------------|
| ✅ **Économie RAM** | Services partagés = -400-500 MB économisés |
| ✅ **Économie Coût** | 1 serveur au lieu de 2 = 5.99€/mois |
| ✅ **Simplicité** | 1 seul docker-compose pour tout |
| ✅ **Isolation** | 2 bases PostgreSQL distinctes |
| ✅ **Scaling** | Upgrade facile vers 8 GB si besoin |

---

## 🛠️ Installation Pas-à-Pas

### 1. Préparer le Serveur

```bash
# SSH vers votre serveur Helsinki
ssh root@VOTRE_IP_HELSINKI

# Mettre à jour le système
apt update && apt upgrade -y

# Installer Docker + Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install docker-compose-plugin -y

# Vérifier l'installation
docker --version
docker compose version
```

### 2. Cloner le Projet Scraper-Pro

```bash
cd /opt
git clone https://github.com/VOTRE-USERNAME/scraper-pro.git
cd scraper-pro

# Vérifier les fichiers optimisés
ls -lh docker-compose.optimized.yml
ls -lh .env.optimized
ls -lh scripts/postgres-init.sh
```

### 3. Configurer les Variables d'Environnement

```bash
# Copier le template optimisé
cp .env.optimized .env

# Générer des mots de passe forts automatiquement
./scripts/generate-secrets.sh

# OU manuellement :
nano .env

# Modifier ces valeurs OBLIGATOIREMENT :
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
# - API_HMAC_SECRET
# - DASHBOARD_PASSWORD
```

**Script de génération automatique** (recommandé) :

```bash
cat > /opt/scraper-pro/scripts/generate-secrets.sh <<'EOF'
#!/bin/bash
set -e

echo "🔐 Génération des secrets cryptographiques..."

# PostgreSQL
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" .env

# Redis
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
sed -i "s|REDIS_PASSWORD=.*|REDIS_PASSWORD=$REDIS_PASSWORD|" .env

# API HMAC
API_HMAC_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
sed -i "s|API_HMAC_SECRET=.*|API_HMAC_SECRET=$API_HMAC_SECRET|" .env

# Dashboard
DASHBOARD_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
sed -i "s|DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD|" .env

# Backlink Engine APP_KEY (format Laravel)
APP_KEY="base64:$(openssl rand -base64 32)"
sed -i "s|APP_KEY=.*|APP_KEY=$APP_KEY|" .env

echo "✅ Secrets générés avec succès !"
echo ""
echo "📄 Secrets sauvegardés dans .env"
echo ""
echo "⚠️  IMPORTANT : Sauvegarder ces secrets dans un endroit sûr :"
echo ""
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
echo "API_HMAC_SECRET=$API_HMAC_SECRET"
echo "DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD"
echo "APP_KEY=$APP_KEY"
EOF

chmod +x /opt/scraper-pro/scripts/generate-secrets.sh
./scripts/generate-secrets.sh
```

### 4. Rendre le Script d'Initialisation PostgreSQL Exécutable

```bash
chmod +x scripts/postgres-init.sh
```

### 5. Adapter la Configuration Backlink Engine

**Si Backlink Engine utilise Laravel/PHP :**

Modifier `docker-compose.optimized.yml` section `backlink-engine` :

```bash
nano docker-compose.optimized.yml

# Rechercher la section "backlink-engine" (ligne ~272)
# Adapter selon votre image Docker ou build
```

**Exemple pour Laravel :**

```yaml
backlink-engine:
  image: votre-registry/backlink-engine:latest
  # OU
  build:
    context: ../backlink-engine
    dockerfile: Dockerfile

  environment:
    DB_CONNECTION: pgsql
    DB_HOST: postgres
    DB_PORT: 5432
    DB_DATABASE: backlink_db
    DB_USERNAME: ${POSTGRES_USER}
    DB_PASSWORD: ${POSTGRES_PASSWORD}

    REDIS_HOST: redis
    REDIS_PORT: 6379
    REDIS_PASSWORD: ${REDIS_PASSWORD}
    REDIS_DB: 1

    APP_ENV: production
    APP_DEBUG: "false"
    APP_KEY: ${APP_KEY}
    APP_URL: ${BACKLINK_URL}

  volumes:
    - ../backlink-engine/storage:/var/www/html/storage
    - ../backlink-engine/.env:/var/www/html/.env
```

### 6. Démarrer les Services

```bash
# Utiliser le docker-compose optimisé
docker compose -f docker-compose.optimized.yml up -d

# Vérifier que tous les containers démarrent
docker compose -f docker-compose.optimized.yml ps

# Suivre les logs
docker compose -f docker-compose.optimized.yml logs -f
```

**Output attendu :**

```
NAME                   STATUS              PORTS
shared-postgres        Up 30 seconds       0.0.0.0:5432->5432/tcp
shared-redis           Up 30 seconds       0.0.0.0:6379->6379/tcp
scraper-api            Up 25 seconds       0.0.0.0:8000->8000/tcp
scraper-worker         Up 25 seconds       -
scraper-dashboard      Up 20 seconds       0.0.0.0:8501->8501/tcp
backlink-engine-app    Up 20 seconds       0.0.0.0:8080->80/tcp
```

### 7. Initialiser les Bases de Données

**Pour Scraper-Pro :**

```bash
# Appliquer les migrations
docker exec scraper-api python -m alembic upgrade head

# OU si vous utilisez les scripts SQL :
docker exec -i shared-postgres psql -U shared_user -d scraper_db < db/migrations/001_initial_schema.sql
docker exec -i shared-postgres psql -U shared_user -d scraper_db < db/migrations/002_add_indexes.sql
# ... répéter pour tous les fichiers de migration
```

**Pour Backlink Engine :**

```bash
# Laravel migrations (exemple)
docker exec backlink-engine-app php artisan migrate --force

# OU commande spécifique à votre Backlink Engine
```

### 8. Vérifier le Bon Fonctionnement

```bash
# Vérifier Scraper-Pro API
curl http://localhost:8000/health
# Attendu : {"status":"healthy"}

# Vérifier PostgreSQL (2 bases créées)
docker exec shared-postgres psql -U shared_user -c "\l"
# Attendu : scraper_db et backlink_db dans la liste

# Vérifier Redis
docker exec shared-redis redis-cli -a $REDIS_PASSWORD ping
# Attendu : PONG

# Vérifier RAM utilisée
docker stats --no-stream
```

**Output attendu (RAM) :**

```
CONTAINER             MEM USAGE / LIMIT
shared-postgres       280MB / 500MB     (56%)
shared-redis          85MB / 150MB      (56%)
scraper-api           320MB / 400MB     (80%)
scraper-worker        580MB / 700MB     (82%)
scraper-dashboard     240MB / 350MB     (68%)
backlink-engine-app   620MB / 800MB     (77%)
-------------------------------------------------
TOTAL                 ~2.1 GB / 4 GB    (52%)
```

---

## 🔍 Monitoring RAM en Continu

### Script de Monitoring Automatique

```bash
cat > /usr/local/bin/monitor-ram.sh <<'EOF'
#!/bin/bash

echo "=========================================="
echo "📊 RAM Monitoring - Dual Apps"
echo "=========================================="
echo ""

# RAM système
echo "🖥️  Système :"
free -h | grep Mem

echo ""
echo "🐳 Docker Containers :"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

echo ""

# Calcul total RAM Docker
TOTAL_RAM=$(docker stats --no-stream --format "{{.MemUsage}}" | awk '{print $1}' | sed 's/MiB//' | awk '{s+=$1} END {print s}')
echo "📦 Total Docker : ${TOTAL_RAM} MB"

# Alerte si > 90%
TOTAL_SYSTEM=$(free -m | grep Mem | awk '{print $2}')
USED_SYSTEM=$(free -m | grep Mem | awk '{print $3}')
PERCENT=$((100 * USED_SYSTEM / TOTAL_SYSTEM))

if [ $PERCENT -gt 90 ]; then
  echo ""
  echo "⚠️  ALERTE : RAM utilisation à ${PERCENT}%"
  echo "    Recommandation : Réduire CONCURRENT_REQUESTS à 2"
fi

echo "=========================================="
EOF

chmod +x /usr/local/bin/monitor-ram.sh

# Exécuter manuellement
/usr/local/bin/monitor-ram.sh

# OU cron toutes les 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/monitor-ram.sh >> /var/log/ram-monitor.log") | crontab -
```

---

## ⚙️ Ajustements selon la Charge

### Si RAM dépasse 90%

**Option 1 : Réduire CONCURRENT_REQUESTS**

```bash
nano .env

# Modifier :
CONCURRENT_REQUESTS=2  # Au lieu de 3
CONCURRENT_REQUESTS_PER_DOMAIN=1

# Redémarrer le scraper
docker compose -f docker-compose.optimized.yml restart scraper-worker
```

**Option 2 : Planifier les Tâches Lourdes**

```bash
# Crontab : Scraper la NUIT (2h-6h)
crontab -e

# Ajouter :
0 2 * * * docker exec scraper-api curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple -H "Content-Type: application/json" -d '{"source_type":"custom_urls","name":"Nightly Scrape","config":{"urls":["https://www.expat.com/fr/guide/"]},"max_results":1000}'

# Backlink Engine : Tâches le JOUR (10h-18h)
0 10 * * * docker exec backlink-engine-app php artisan backlinks:generate
```

**Option 3 : Désactiver Temporairement un Service**

```bash
# Stopper le Dashboard si non utilisé
docker compose -f docker-compose.optimized.yml stop scraper-dashboard

# Économie : ~350 MB RAM
```

---

## 📈 Upgrade vers 8 GB RAM (si nécessaire)

### Quand upgrader ?

- RAM utilisée constamment > 85%
- Scraping lent (throttling excessif)
- Backlink Engine ralenti

### Comment upgrader sur Hetzner ?

```bash
# 1. Via Hetzner Cloud Console
# Serveur → Resize → CPX31 (4 vCPU, 8 GB, 11.90€/mois)

# 2. Après upgrade, ajuster la config
nano .env

# Augmenter les ressources :
CONCURRENT_REQUESTS=6  # Au lieu de 3
CONCURRENT_REQUESTS_PER_DOMAIN=2

# 3. Décommenter le monitoring dans docker-compose.optimized.yml
nano docker-compose.optimized.yml

# Décommenter :
# - prometheus
# - grafana
# - nginx (reverse proxy)

# 4. Redémarrer
docker compose -f docker-compose.optimized.yml down
docker compose -f docker-compose.optimized.yml up -d
```

---

## 🔐 Sécurité & Firewall

```bash
# Installer UFW (firewall)
apt install ufw -y

# Autoriser SSH
ufw allow 22/tcp

# Autoriser HTTP/HTTPS (si vous utilisez Nginx)
ufw allow 80/tcp
ufw allow 443/tcp

# Autoriser les ports applicatifs UNIQUEMENT depuis votre IP
ufw allow from VOTRE_IP_BUREAU to any port 8000  # API
ufw allow from VOTRE_IP_BUREAU to any port 8501  # Dashboard
ufw allow from VOTRE_IP_BUREAU to any port 8080  # Backlink Engine

# Activer le firewall
ufw enable

# Vérifier
ufw status
```

---

## 🆘 Troubleshooting

### Problème : Container PostgreSQL ne démarre pas

```bash
# Vérifier les logs
docker compose -f docker-compose.optimized.yml logs postgres

# Erreur fréquente : Permission sur postgres-init.sh
chmod +x scripts/postgres-init.sh

# Nettoyer et redémarrer
docker compose -f docker-compose.optimized.yml down -v
docker compose -f docker-compose.optimized.yml up -d postgres
```

### Problème : RAM dépasse 95%

```bash
# Solution d'urgence : Redémarrer containers gourmands
docker compose -f docker-compose.optimized.yml restart scraper-worker

# Réduire CONCURRENT_REQUESTS à 2
nano .env
# CONCURRENT_REQUESTS=2

docker compose -f docker-compose.optimized.yml restart scraper-worker scraper-api
```

### Problème : Backlink Engine ne se connecte pas à PostgreSQL

```bash
# Vérifier que les 2 bases existent
docker exec shared-postgres psql -U shared_user -c "\l"

# Vérifier les credentials dans .env
docker exec backlink-engine-app env | grep DB_

# Tester la connexion manuellement
docker exec shared-postgres psql -U shared_user -d backlink_db -c "SELECT 1"
```

---

## 📊 Capacités Réalistes

| Métrique | Capacité (2 vCPU, 4 GB) |
|----------|-------------------------|
| **URLs scrapées/jour** | 20,000-30,000 |
| **Contacts collectés/jour** | 5,000-10,000 |
| **Backlinks générés/jour** | Selon Backlink Engine |
| **Stockage utilisé** | ~15-25 GB / 80 GB |
| **RAM moyenne** | 2.5-3.0 GB / 4 GB |
| **Uptime** | 99%+ (redémarrages automatiques) |

---

## 💰 Coûts Totaux

| Scénario | Serveur | Proxies | Total/mois |
|----------|---------|---------|------------|
| **URLs uniquement** | 5.99€ | 0€ | **5.99€** ✅ |
| **URLs + Google (futur)** | 5.99€ + 11.90€ | 75€ | **92.89€** |
| **Upgrade vers 8 GB** | 11.90€ | 0€ | **11.90€** |

---

## ✅ Checklist Finale

- [ ] Docker + Docker Compose installés
- [ ] Secrets générés automatiquement
- [ ] `postgres-init.sh` exécutable
- [ ] Configuration Backlink Engine adaptée
- [ ] Services démarrés (`docker compose ps`)
- [ ] PostgreSQL : 2 bases créées (`\l`)
- [ ] Redis : accessible (`PING`)
- [ ] Scraper API : health check OK
- [ ] RAM monitoring configuré
- [ ] Firewall activé (UFW)
- [ ] Backups automatiques planifiés (cron)

---

**Votre configuration dual-app optimisée est prête ! 🎉**

Pour plus d'aide, consultez :
- `README.md` : Documentation principale
- `docs/DEPLOYMENT.md` : Déploiement production
- `docs/API.md` : Référence API
