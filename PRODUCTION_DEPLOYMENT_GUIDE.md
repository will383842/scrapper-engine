# Scraper-Pro - Guide de Déploiement Production

**Version:** 2.0.0
**Date:** 2026-02-13
**Serveur:** Hetzner CPX31 (4 vCPU, 8GB RAM, 160GB SSD)
**Mode:** URLs Only (PAS de proxies, PAS de Google)

---

## Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Installation Automatique](#installation-automatique)
4. [Configuration Manuelle](#configuration-manuelle)
5. [Sécurité](#sécurité)
6. [Monitoring](#monitoring)
7. [Maintenance](#maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Vue d'Ensemble

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NGINX (Reverse Proxy)                    │
│                  SSL/TLS (Let's Encrypt)                    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
┌───────▼────────┐                         ┌────────▼────────┐
│   Dashboard    │                         │   Grafana       │
│  (Streamlit)   │                         │  (Monitoring)   │
│   Port: 8501   │                         │   Port: 3000    │
└────────────────┘                         └─────────────────┘
        │                                           │
        │                                           │
┌───────▼────────────────────────────────────────────────────┐
│                    Scraper API (FastAPI)                   │
│                        Port: 8000                          │
└─────────────────────┬──────────────────┬──────────────────┘
                      │                  │
          ┌───────────▼──────┐  ┌────────▼─────────┐
          │   PostgreSQL 16  │  │    Redis 7       │
          │   Port: 5432     │  │   Port: 6379     │
          │   (Dedup Cache)  │  │   (Job Queue)    │
          └──────────────────┘  └──────────────────┘
                      │
          ┌───────────▼──────────────────┐
          │   Prometheus + Loki Stack   │
          │   (Metrics + Logs)          │
          └─────────────────────────────┘
```

### Services Docker

| Service | Container | Ports | RAM | CPU | Description |
|---------|-----------|-------|-----|-----|-------------|
| PostgreSQL | scraper-postgres | 5432 | 2GB | 1.5 | Base de données principale |
| Redis | scraper-redis | 6379 | 1GB | 0.5 | Cache + Deduplication |
| Scraper API | scraper-app | 8000 | 3GB | 2.0 | FastAPI + Scrapy |
| Dashboard | scraper-dashboard | 8501 | 1GB | 0.5 | Streamlit Premium UI |
| Prometheus | scraper-prometheus | 9090 | 512MB | 0.5 | Métriques |
| Grafana | scraper-grafana | 3000 | 512MB | 0.5 | Visualisation |
| Loki | scraper-loki | 3100 | 512MB | 0.5 | Logs agrégés |
| Promtail | scraper-promtail | - | 256MB | 0.25 | Log collector |
| Alertmanager | scraper-alertmanager | 9093 | 256MB | 0.25 | Alertes |

**Total RAM utilisée:** ~7.5GB sur 8GB disponibles (6% réservé système)

---

## Prérequis

### Serveur

- **OS:** Ubuntu 22.04 LTS ou Debian 12+
- **CPU:** 4 vCPU minimum
- **RAM:** 8GB minimum
- **Stockage:** 160GB SSD (NVMe recommandé)
- **Réseau:** 1 Gbit/s (20TB/mois inclus)

### Accès

```bash
# SSH avec clé publique (PAS de mot de passe)
ssh root@your-server-ip

# Créer un utilisateur non-root
adduser scraper
usermod -aG sudo scraper
su - scraper
```

### Logiciels requis

- Docker Engine 24+
- Docker Compose v2.24+
- Git
- UFW (firewall)
- Nginx (pour reverse proxy)
- Certbot (pour SSL Let's Encrypt)

---

## Installation Automatique

### Étape 1: Cloner le projet

```bash
cd /home/scraper
git clone https://github.com/YOUR_REPO/scraper-pro.git
cd scraper-pro
```

### Étape 2: Lancer le script d'initialisation

```bash
# Installation complète automatique (RECOMMANDÉ)
bash scripts/init-production.sh

# Options disponibles:
bash scripts/init-production.sh --skip-secrets  # Utiliser .env existant
bash scripts/init-production.sh --no-firewall   # Skip UFW config
bash scripts/init-production.sh --dry-run       # Check only
```

Le script effectue:

1. ✅ Vérification des prérequis (Docker, Docker Compose)
2. ✅ Génération des secrets sécurisés (PostgreSQL, Redis, API, Grafana)
3. ✅ Création du fichier `.env` depuis `.env.production`
4. ✅ Configuration du firewall UFW (ports 22, 80, 443)
5. ✅ Pull des images Docker
6. ✅ Build des images d'application
7. ✅ Démarrage des services
8. ✅ Health checks automatiques
9. ✅ Sauvegarde des secrets dans `~/.scraper-pro-secrets-*.txt`

**Durée estimée:** 5-10 minutes

### Étape 3: Sauvegarder les secrets

```bash
# Les secrets sont sauvegardés dans un fichier temporaire
cat ~/.scraper-pro-secrets-*.txt

# IMPORTANT: Copier dans un gestionnaire de mots de passe
# Puis supprimer le fichier
rm ~/.scraper-pro-secrets-*.txt
```

### Étape 4: Configurer MailWizz et Webhooks

```bash
nano .env

# Mettre à jour ces variables:
MAILWIZZ_SOS_EXPAT_API_KEY=your_real_api_key
MAILWIZZ_ULIXAI_API_KEY=your_real_api_key
WEBHOOK_SOS_EXPAT_SECRET=shared_secret_with_sos_expat
WEBHOOK_ULIXAI_SECRET=shared_secret_with_ulixai

# Redémarrer les services
docker-compose -f docker-compose.production.yml restart
```

---

## Configuration Manuelle

### 1. Générer les secrets

```bash
# PostgreSQL password (32 chars)
openssl rand -base64 32 | tr -d "=+/" | cut -c1-32

# Redis password (32 chars)
openssl rand -base64 32 | tr -d "=+/" | cut -c1-32

# API HMAC secret (64 chars)
openssl rand -base64 64 | tr -d "=+/" | cut -c1-64

# Dashboard password (24 chars)
openssl rand -base64 24 | tr -d "=+/" | cut -c1-24

# Grafana password (24 chars)
openssl rand -base64 24 | tr -d "=+/" | cut -c1-24
```

### 2. Créer le fichier .env

```bash
cp .env.production .env
chmod 600 .env
nano .env

# Remplacer TOUS les "CHANGE_ME" par les secrets générés
```

### 3. Démarrer les services

```bash
# Pull images
docker-compose -f docker-compose.production.yml pull

# Build images
docker-compose -f docker-compose.production.yml build --no-cache

# Start services
docker-compose -f docker-compose.production.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.production.yml logs -f
```

### 4. Vérifier le statut

```bash
# Statut des containers
docker ps

# Health checks
curl http://localhost:8000/health          # API
curl http://localhost:8501                 # Dashboard
curl http://localhost:3000/api/health      # Grafana
curl http://localhost:9090/-/healthy       # Prometheus
```

---

## Sécurité

### Firewall UFW

```bash
# Activer UFW
sudo ufw enable

# Autoriser SSH (CRITIQUE - ne pas oublier!)
sudo ufw allow 22/tcp

# Autoriser HTTP/HTTPS (pour Nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Vérifier le statut
sudo ufw status verbose
```

**IMPORTANT:** Les services internes (8000, 8501, 3000, etc.) sont bindés sur `127.0.0.1` uniquement et **NE SONT PAS** exposés à Internet.

### Nginx Reverse Proxy

```bash
# Installer Nginx
sudo apt install nginx

# Créer la configuration
sudo nano /etc/nginx/sites-available/scraper-pro
```

```nginx
# Dashboard (Streamlit)
server {
    listen 80;
    server_name dashboard.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}

# Grafana
server {
    listen 80;
    server_name monitoring.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Activer la config
sudo ln -s /etc/nginx/sites-available/scraper-pro /etc/nginx/sites-enabled/

# Tester la config
sudo nginx -t

# Recharger Nginx
sudo systemctl reload nginx
```

### SSL avec Let's Encrypt

```bash
# Installer Certbot
sudo apt install certbot python3-certbot-nginx

# Obtenir les certificats SSL
sudo certbot --nginx -d dashboard.your-domain.com -d monitoring.your-domain.com

# Renouvellement automatique (cron job déjà créé par Certbot)
sudo certbot renew --dry-run
```

### Fail2ban (Protection SSH)

```bash
# Installer Fail2ban
sudo apt install fail2ban

# Créer la configuration locale
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local

# Activer la protection SSH
[sshd]
enabled = true
port = 22
maxretry = 3
bantime = 3600

# Redémarrer Fail2ban
sudo systemctl restart fail2ban

# Vérifier le statut
sudo fail2ban-client status sshd
```

### Permissions des fichiers

```bash
# .env doit être lisible uniquement par le propriétaire
chmod 600 .env

# Vérifier
ls -la .env
# Doit afficher: -rw------- 1 scraper scraper ...
```

---

## Monitoring

### Accès Grafana

1. **URL:** `https://monitoring.your-domain.com`
2. **Username:** `admin`
3. **Password:** Voir le fichier de secrets généré

### Dashboards Disponibles

1. **Scraper-Pro Production Dashboard** (`scraper-production.json`)
   - URLs scrapées (total + taux)
   - Emails extraits (total + taux)
   - CPU/RAM usage
   - PostgreSQL/Redis stats
   - Deduplication stats
   - HTTP response codes
   - Request duration (p95, p99)
   - Service health

### Prometheus Queries

```promql
# URLs scrapées par minute
rate(scraper_total_urls_scraped[5m]) * 60

# Emails extraits par minute
rate(scraper_total_emails_extracted[5m]) * 60

# CPU usage
100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])))

# Memory usage
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))

# PostgreSQL connections
pg_stat_database_numbackends{datname="scraper_db"}

# Redis keys count
redis_db_keys{db="db0"}

# Deduplication stats
scraper_dedup_urls_blocked
scraper_dedup_emails_blocked
```

### Alertes Prometheus

Fichier: `monitoring/alertmanager/alertmanager.yml`

Alertes configurées:

- **HighCPUUsage:** CPU > 80% pendant 5 minutes
- **HighMemoryUsage:** RAM > 85% pendant 5 minutes
- **HighDiskUsage:** Disque > 85%
- **PostgreSQLDown:** PostgreSQL indisponible
- **RedisDown:** Redis indisponible
- **ScraperAPIDown:** API indisponible
- **SlowScrapingRate:** < 10 URLs/minute pendant 15 minutes

### Logs

```bash
# Logs de tous les services
docker-compose -f docker-compose.production.yml logs -f

# Logs d'un service spécifique
docker logs scraper-app -f
docker logs scraper-postgres -f
docker logs scraper-redis -f

# Logs dans Grafana Loki
# Accéder à Grafana > Explore > Loki
# Query: {container_name="scraper-app"}
```

---

## Maintenance

### Backups PostgreSQL

```bash
# Backup manuel
bash scripts/backup-postgres.sh

# Restauration
bash scripts/restore-postgres.sh /path/to/backup.sql.gz

# Backup automatique quotidien (cron)
crontab -e

# Ajouter cette ligne (backup à 2h du matin)
0 2 * * * /home/scraper/scraper-pro/scripts/backup-postgres.sh
```

### Backups Redis

```bash
# Redis sauvegarde automatiquement (RDB + AOF)
# Fichiers dans le volume redis_data

# Backup manuel
docker exec scraper-redis redis-cli -a "$REDIS_PASSWORD" BGSAVE

# Vérifier le dernier backup
docker exec scraper-redis redis-cli -a "$REDIS_PASSWORD" LASTSAVE
```

### Mises à jour

```bash
# Arrêter les services
docker-compose -f docker-compose.production.yml stop

# Mettre à jour le code
git pull origin main

# Rebuild les images
docker-compose -f docker-compose.production.yml build --no-cache

# Redémarrer
docker-compose -f docker-compose.production.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.production.yml logs -f
```

### Nettoyage

```bash
# Nettoyer les images Docker inutilisées
docker system prune -a --volumes

# Nettoyer les logs Docker
sudo sh -c 'truncate -s 0 /var/lib/docker/containers/*/*-json.log'

# VACUUM PostgreSQL (automatique mais peut être forcé)
docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c "VACUUM ANALYZE;"

# Nettoyer Redis (supprimer les clés expirées)
docker exec scraper-redis redis-cli -a "$REDIS_PASSWORD" --scan --pattern "*" | xargs -L 1 redis-cli -a "$REDIS_PASSWORD" DEL
```

### Rotation des logs

Fichier: `/etc/logrotate.d/scraper-pro`

```logrotate
/home/scraper/scraper-pro/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 scraper scraper
}
```

---

## Troubleshooting

### Problème: PostgreSQL ne démarre pas

**Cause:** Permissions incorrectes sur le volume

```bash
# Vérifier les logs
docker logs scraper-postgres

# Supprimer le volume et recréer
docker-compose -f docker-compose.production.yml down -v
docker-compose -f docker-compose.production.yml up -d postgres
```

### Problème: Redis nécessite un mot de passe

**Cause:** REDIS_PASSWORD non défini ou incorrect

```bash
# Vérifier la variable
docker exec scraper-redis env | grep REDIS_PASSWORD

# Tester la connexion
docker exec scraper-redis redis-cli -a "$REDIS_PASSWORD" PING
# Doit retourner: PONG
```

### Problème: API health check échoue

**Cause:** Service non démarré ou erreur de configuration

```bash
# Vérifier les logs
docker logs scraper-app -f

# Vérifier les variables d'environnement
docker exec scraper-app env | grep POSTGRES
docker exec scraper-app env | grep REDIS

# Redémarrer le service
docker-compose -f docker-compose.production.yml restart scraper
```

### Problème: Dashboard Streamlit ne charge pas

**Cause:** Port 8501 non accessible ou service crashé

```bash
# Vérifier le statut
docker ps | grep dashboard

# Vérifier les logs
docker logs scraper-dashboard -f

# Redémarrer
docker-compose -f docker-compose.production.yml restart dashboard
```

### Problème: Grafana ne se connecte pas à Prometheus

**Cause:** Data source non configurée

```bash
# Accéder à Grafana
# Configuration > Data Sources > Add data source > Prometheus

# URL: http://prometheus:9090
# Access: Server (default)
# Save & Test
```

### Problème: Scraping rate trop faible

**Cause:** Limites de rate limiting ou configuration sous-optimale

```bash
# Ajuster dans .env
CONCURRENT_REQUESTS=32              # Augmenter (16 -> 32)
CONCURRENT_REQUESTS_PER_DOMAIN=8    # Augmenter (4 -> 8)
DOWNLOAD_DELAY=0.5                  # Réduire (1.0 -> 0.5)

# Redémarrer
docker-compose -f docker-compose.production.yml restart scraper
```

### Problème: Out of Memory

**Cause:** Trop de services ou fuites mémoire

```bash
# Vérifier l'utilisation mémoire
docker stats

# Identifier le coupable
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"

# Réduire les limites dans docker-compose.production.yml
# Redémarrer les services gourmands
```

---

## Performance Attendue

### Mode URLs Only (CPX31, 4 vCPU, 8GB RAM)

| Métrique | Valeur |
|----------|--------|
| **URLs/minute** | 50-100 |
| **URLs/heure** | 3,000-6,000 |
| **URLs/jour** | 70,000-150,000 |
| **Emails/jour** | 10,000-30,000 (dépend des sites) |
| **CPU moyen** | 40-60% |
| **RAM moyenne** | 6-7GB / 8GB |
| **Stockage/jour** | 500MB-1GB (logs + données) |
| **Bande passante/jour** | 5-10GB |

### Coûts Mensuels Estimés

| Composant | Coût |
|-----------|------|
| **Hetzner CPX31** | €10.49/mois (~$11.50) |
| **Domaine + SSL** | €10/an (~$1/mois) |
| **Backups offsite** | €5-10/mois (optionnel) |
| **Total** | **~$15-20/mois** |

**Remarque:** Aucun coût de proxies car mode URLs Only (économie de $500-2000/mois!)

---

## Commandes Utiles

```bash
# ─── Docker ───────────────────────────────────────────────

# Voir tous les containers
docker ps

# Logs en temps réel
docker-compose -f docker-compose.production.yml logs -f

# Redémarrer un service
docker-compose -f docker-compose.production.yml restart scraper

# Arrêter tous les services
docker-compose -f docker-compose.production.yml stop

# Démarrer tous les services
docker-compose -f docker-compose.production.yml start

# Reconstruire et redémarrer
docker-compose -f docker-compose.production.yml up -d --build

# ─── PostgreSQL ───────────────────────────────────────────

# Accéder au shell PostgreSQL
docker exec -it scraper-postgres psql -U scraper_admin -d scraper_db

# Vérifier la taille de la DB
docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c "SELECT pg_size_pretty(pg_database_size('scraper_db'));"

# Lister les tables
docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c "\dt"

# ─── Redis ────────────────────────────────────────────────

# Accéder au CLI Redis
docker exec -it scraper-redis redis-cli -a "$REDIS_PASSWORD"

# Vérifier le nombre de clés
docker exec scraper-redis redis-cli -a "$REDIS_PASSWORD" DBSIZE

# Info mémoire
docker exec scraper-redis redis-cli -a "$REDIS_PASSWORD" INFO memory

# ─── Monitoring ───────────────────────────────────────────

# CPU/RAM usage en temps réel
docker stats

# Espace disque
df -h

# Trafic réseau
docker exec scraper-app cat /proc/net/dev

# ─── Logs ─────────────────────────────────────────────────

# Logs d'un service
docker logs scraper-app -f --tail 100

# Logs système
journalctl -u docker -f

# ─── Sécurité ─────────────────────────────────────────────

# Statut UFW
sudo ufw status verbose

# Bannissements Fail2ban
sudo fail2ban-client status sshd

# Connexions SSH actives
who
```

---

## Support et Documentation

### Documentation

- **README.md** - Vue d'ensemble du projet
- **ULTRA_PRO_SYSTEM_READY.md** - Architecture complète
- **docs/DEDUPLICATION_SYSTEM.md** - Système de déduplication
- **FAQ_CRITIQUE.md** - Questions fréquentes
- **DEPLOYMENT_PRODUCTION.md** - Guide de déploiement (ancien)

### Logs de Déploiement

- **FINAL_STATUS.md** - État final du projet
- **PRODUCTION_READINESS_GAPS.md** - Écarts de production

### Contact

Pour toute question ou problème:

1. Consulter la FAQ: `FAQ_CRITIQUE.md`
2. Vérifier les logs: `docker-compose logs -f`
3. Consulter Grafana: `https://monitoring.your-domain.com`

---

## Checklist de Déploiement

Avant de marquer le déploiement comme terminé, vérifier:

### Sécurité

- [ ] Firewall UFW activé (ports 22, 80, 443)
- [ ] Services bindés sur 127.0.0.1 uniquement
- [ ] Nginx reverse proxy configuré avec SSL
- [ ] Let's Encrypt configuré et auto-renouvelable
- [ ] Fail2ban activé pour SSH
- [ ] Permissions `.env` = 600
- [ ] Secrets sauvegardés dans gestionnaire de mots de passe
- [ ] Fichier de secrets temporaire supprimé

### Configuration

- [ ] Toutes les variables `.env` configurées (pas de CHANGE_ME)
- [ ] MailWizz API keys configurées
- [ ] Webhook secrets partagés avec SOS-Expat/Ulixai
- [ ] Mode scraping = `urls_only`
- [ ] Deduplication activée (ULTRA mode)

### Services

- [ ] PostgreSQL: healthy
- [ ] Redis: healthy
- [ ] Scraper API: healthy
- [ ] Dashboard: accessible
- [ ] Prometheus: healthy
- [ ] Grafana: accessible
- [ ] Loki: healthy
- [ ] Alertmanager: configuré

### Monitoring

- [ ] Dashboard Grafana accessible via HTTPS
- [ ] Data sources Prometheus et Loki configurées
- [ ] Dashboard "Scraper-Pro Production" importé
- [ ] Alertes configurées et testées
- [ ] Logs visibles dans Loki

### Backups

- [ ] Backup PostgreSQL manuel testé
- [ ] Restauration PostgreSQL testée
- [ ] Cron job backup quotidien configuré
- [ ] Backups offsite configurés (optionnel)

### Performance

- [ ] Scraping rate conforme (50-100 URLs/min)
- [ ] CPU usage < 80%
- [ ] RAM usage < 85%
- [ ] Disk usage < 80%
- [ ] Pas d'erreurs dans les logs

### Documentation

- [ ] Guide de déploiement lu et compris
- [ ] Commandes utiles mémorisées
- [ ] Contact support disponible
- [ ] Procédures de maintenance définies

---

## Changelog

### Version 2.0.0 (2026-02-13)

- Configuration production optimale créée
- Script d'initialisation automatique (`init-production.sh`)
- Dashboard Grafana production (`scraper-production.json`)
- Configuration PostgreSQL optimisée (CPX31)
- Mode URLs Only activé par défaut
- Deduplication ULTRA-PRO intégrée
- Monitoring stack complet (Prometheus, Grafana, Loki)
- Guide de déploiement exhaustif

---

**Fin du Guide de Déploiement Production**

Pour toute question, consulter `FAQ_CRITIQUE.md` ou les logs des services.

**Bon déploiement! 🚀**
