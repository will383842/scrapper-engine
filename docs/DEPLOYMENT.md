# 🚀 Guide de Déploiement - Scraper-Pro

Guide complet pour déployer **Scraper-Pro** en production.

---

## 📋 Checklist Pré-Déploiement

```
□ Serveur configuré (4+ CPU, 8+ GB RAM, 50+ GB SSD)
□ Docker 20.10+ et Docker Compose 2.0+ installés
□ .env configuré avec secrets de production
□ Proxies configurés et testés
□ MailWizz API keys valides
□ Backups configurés
□ Monitoring configuré
□ CI/CD pipeline testé
□ DNS configuré (scraper.votre-domaine.com)
□ SSL/TLS certificat prêt (Let's Encrypt)
```

---

## 🖥️ Serveur de Production

### Configuration recommandée

| Ressource | Minimum | Recommandé | Optimal |
|-----------|---------|------------|---------|
| **CPU** | 4 cores | 8 cores | 16 cores |
| **RAM** | 8 GB | 16 GB | 32 GB |
| **Disque** | 50 GB SSD | 100 GB SSD | 200 GB NVMe |
| **Réseau** | 100 Mbps | 1 Gbps | 1 Gbps |

### Fournisseurs recommandés

- **AWS** : t3.xlarge ou c5.2xlarge
- **GCP** : n2-standard-4 ou n2-standard-8
- **DigitalOcean** : CPU-Optimized 8GB ou 16GB
- **OVH** : VPS Elite ou Advance

---

## 📦 Déploiement Initial

### 1. Préparation du serveur

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Installer Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Installer utilitaires
sudo apt install -y git make curl wget htop iotop iftop
```

### 2. Cloner le repository

```bash
# Créer le répertoire de déploiement
sudo mkdir -p /opt/scraper-pro
sudo chown $USER:$USER /opt/scraper-pro

# Cloner (SSH recommandé)
cd /opt/scraper-pro
git clone git@github.com:votre-org/scraper-pro.git .

# Ou via HTTPS
git clone https://github.com/votre-org/scraper-pro.git .
```

### 3. Configuration

```bash
# Copier et éditer .env
cp .env.example .env
nano .env

# Générer secrets sécurisés
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))" >> .env
python3 -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(32))" >> .env
python3 -c "import secrets; print('API_HMAC_SECRET=' + secrets.token_urlsafe(48))" >> .env

# Protéger .env
chmod 600 .env
```

### 4. Initialiser la base de données

```bash
# Démarrer PostgreSQL seulement
docker-compose up -d postgres

# Attendre que PostgreSQL soit prêt
sleep 15

# Vérifier
docker-compose logs postgres | grep "ready to accept connections"

# Initialiser le schéma (déjà fait via init.sql)
# Appliquer les migrations
docker-compose exec postgres psql -U scraper_admin -d scraper_db < db/migrations/002_add_checkpoint_resume.sql
docker-compose exec postgres psql -U scraper_admin -d scraper_db < db/migrations/003_add_scraped_articles.sql
docker-compose exec postgres psql -U scraper_admin -d scraper_db < db/migrations/004_add_compound_indexes.sql
```

### 5. Démarrer tous les services

```bash
# Build et démarrer
docker-compose up -d --build

# Vérifier le statut
docker-compose ps

# Vérifier les logs
docker-compose logs -f
```

### 6. Vérification post-déploiement

```bash
# Health check API
curl http://localhost:8000/health

# Dashboard accessible
curl -I http://localhost:8501

# Grafana accessible
curl -I http://localhost:3000

# Prometheus accessible
curl -I http://localhost:9090
```

---

## 🔒 Configuration SSL/TLS (Production)

### Option A : Nginx Reverse Proxy + Let's Encrypt

```bash
# Installer Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# Configuration Nginx
sudo nano /etc/nginx/sites-available/scraper-pro
```

```nginx
# /etc/nginx/sites-available/scraper-pro

upstream scraper_api {
    server 127.0.0.1:8000;
}

upstream scraper_dashboard {
    server 127.0.0.1:8501;
}

upstream grafana {
    server 127.0.0.1:3000;
}

# API
server {
    listen 80;
    server_name api.scraper-pro.com;

    location / {
        proxy_pass http://scraper_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Dashboard
server {
    listen 80;
    server_name dashboard.scraper-pro.com;

    location / {
        proxy_pass http://scraper_dashboard;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Grafana
server {
    listen 80;
    server_name grafana.scraper-pro.com;

    location / {
        proxy_pass http://grafana;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/scraper-pro /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Obtenir les certificats SSL
sudo certbot --nginx -d api.scraper-pro.com -d dashboard.scraper-pro.com -d grafana.scraper-pro.com

# Renouvellement automatique (cron)
sudo certbot renew --dry-run
```

---

## 🔄 Stratégie de Déploiement

### Déploiement Zero-Downtime

```bash
# 1. Sauvegarder la DB
./scripts/backup-postgres.sh

# 2. Pull les changements
git pull origin main

# 3. Build nouvelle image (sans arrêter)
docker-compose build scraper dashboard

# 4. Déploiement rolling update
docker-compose up -d --no-deps --scale scraper=2 scraper
sleep 10
docker-compose up -d --no-deps --scale scraper=1 scraper

# 5. Vérifier
curl http://localhost:8000/health
```

### Rollback

```bash
# Revenir au commit précédent
git log --oneline -5  # Voir l'historique
git checkout <commit-hash>

# Reconstruire
docker-compose build scraper dashboard

# Redéployer
docker-compose up -d scraper dashboard
```

---

## 📊 Monitoring en Production

### Accès aux dashboards

| Service | URL | Auth |
|---------|-----|------|
| **API** | https://api.scraper-pro.com | HMAC |
| **Dashboard** | https://dashboard.scraper-pro.com | Password |
| **Grafana** | https://grafana.scraper-pro.com | admin / GRAFANA_PASSWORD |
| **Prometheus** | http://localhost:9090 | - |

### Alertes configurées

Voir `monitoring/prometheus/alerts/scraper.yml` :
- ✅ Service down (critical)
- ✅ High job failure rate (warning)
- ✅ MailWizz sync issues (warning)
- ✅ High memory/disk usage (warning)
- ✅ PostgreSQL connection issues (warning)

### Notifications

Configurées via Alertmanager :
- 📧 Email : `ALERT_EMAIL_TO`
- 💬 Slack : `SLACK_WEBHOOK_URL` (optionnel)

---

## 💾 Backups en Production

### Configuration cron

```bash
# Éditer le cron
sudo crontab -e

# Ajouter cette ligne (backup quotidien à 3h00 AM)
0 3 * * * /opt/scraper-pro/scripts/backup-postgres.sh >> /var/log/scraper-backup.log 2>&1
```

### Upload vers S3 (optionnel)

```bash
# Installer AWS CLI
sudo apt install -y awscli

# Configurer credentials
aws configure

# Ajouter dans .env
echo "AWS_S3_BUCKET=scraper-pro-backups" >> .env

# Le script backup-postgres.sh uploade automatiquement vers S3
```

### Tester la restauration (staging)

```bash
# Télécharger le backup le plus récent
aws s3 cp s3://scraper-pro-backups/scraper_db_latest.sql.gz ./

# Restaurer
./scripts/restore-postgres.sh scraper_db_latest.sql.gz
```

---

## 🔧 Maintenance

### Logs

```bash
# Voir les logs en temps réel
docker-compose logs -f scraper

# Logs des 1000 dernières lignes
docker-compose logs --tail=1000 scraper

# Logs Loki (via Grafana)
# Grafana → Explore → Loki → {job="scraper"}
```

### Nettoyage

```bash
# Nettoyer les images Docker inutilisées
docker system prune -a -f

# Nettoyer les logs anciens (> 7 jours)
find /var/log/scraper-pro -name "*.log" -mtime +7 -delete

# Nettoyer les backups anciens (> 30 jours)
find /var/backups/scraper-pro -name "*.sql.gz" -mtime +30 -delete
```

### Mise à jour

```bash
# Arrêter les services
docker-compose down

# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Redémarrer
docker-compose up -d
```

---

## 🔥 Troubleshooting Production

### Service ne démarre pas

```bash
# Vérifier les logs
docker-compose logs scraper

# Vérifier l'.env
cat .env | grep -v "^#" | grep -v "^$"

# Reconstruire from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Performance dégradée

```bash
# Vérifier les ressources
docker stats

# Vérifier PostgreSQL
docker-compose exec postgres psql -U scraper_admin -d scraper_db -c "
SELECT pid, usename, application_name, state, query_start, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;
"

# Vérifier les slow queries
# Grafana → PostgreSQL Dashboard → Slow Queries
```

### MailWizz sync échoue

```bash
# Vérifier les credentials
curl -v https://mail.sos-expat.com/api/lists

# Vérifier les logs
docker-compose logs scraper | grep mailwizz

# Relancer manuellement
docker-compose exec scraper python -m scraper.jobs.sync_to_mailwizz
```

---

## 📚 Ressources

- 📖 [README](../README.md)
- 🏗️ [Architecture](ARCHITECTURE.md)
- 📦 [Installation](INSTALLATION.md)
- 🔌 [API Reference](API.md)

---

**Production ready !** 🎉
