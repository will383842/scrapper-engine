# 🚀 Guide de Déploiement SCRAPER-PRO

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Pré-requis](#pré-requis)
3. [MODE 1 : Scraping Massif (avec proxies)](#mode-1-scraping-massif-avec-proxies)
4. [MODE 2 : Scraping Simple (sans proxies)](#mode-2-scraping-simple-sans-proxies)
5. [Configuration](#configuration)
6. [Lancement](#lancement)
7. [Vérifications](#vérifications)
8. [Backup & Monitoring](#backup--monitoring)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Introduction

SCRAPER-PRO offre **DEUX modes de déploiement** selon vos besoins :

### 🔵 MODE 1 : SCRAPING MASSIF (Recommandé)
- ✅ **Avec proxies** rotatifs (résidentiels + datacenter)
- ✅ **9 sources** : Google Search, Google Maps, LinkedIn, Facebook, Instagram, YouTube, Forums, URLs custom
- ✅ **10K-20K contacts/mois**
- ✅ **Anti-détection** avancée
- 💰 **Budget** : ~280€/mois
- 🎯 **Pour** : Scraping professionnel, multi-sources, volumes élevés

### 🟢 MODE 2 : SCRAPING SIMPLE (Économique)
- ✅ **Sans proxies** (IP fixe VPS)
- ✅ **1 source** : URLs personnalisées uniquement (generic_url_spider)
- ✅ **2K-5K contacts/mois**
- ✅ **Configuration** minimale
- 💰 **Budget** : ~80€/mois
- 🎯 **Pour** : Scraping ponctuel, sites simples, budget limité

---

## 🛠️ Pré-requis

### Serveur VPS

**Configuration minimale** :
- **CPU** : 4 vCPU
- **RAM** : 8 GB
- **Disque** : 50 GB SSD
- **OS** : Ubuntu 22.04 LTS (recommandé) ou Debian 11+
- **Réseau** : IP publique fixe

**Providers recommandés** :
- 🥇 **Hetzner** (30€/mois) - CPX31
- 🥈 **DigitalOcean** (48$/mois) - 8GB Droplet
- 🥉 **OVH** (35€/mois) - VPS Elite

### Logiciels requis

```bash
# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Installer Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Vérifier installation
docker --version
docker-compose --version
```

### Clés API requises

**OBLIGATOIRES** (les deux modes) :
- ✅ **MailWizz SOS-Expat** API Key
- ✅ **MailWizz Ulixai** API Key

**MODE 1 UNIQUEMENT** :
- ✅ **Oxylabs** (ou SmartProxy, BrightData) credentials
- ✅ **SerpAPI** key (pour Google Search)
- 📌 **2Captcha** key (optionnel, pour LinkedIn/Facebook)

---

## 🔵 MODE 1 : Scraping Massif (avec proxies)

### Étape 1 : Connexion VPS

```bash
# Connexion SSH
ssh root@VOTRE_IP_VPS

# Créer utilisateur scraper
adduser scraper
usermod -aG sudo,docker scraper

# Passer en utilisateur scraper
su - scraper
```

### Étape 2 : Clone du projet

```bash
# Créer dossier projets
mkdir -p ~/projets
cd ~/projets

# Clone repository (ajustez l'URL selon votre repo)
git clone https://github.com/votre-username/scraper-pro.git
cd scraper-pro
```

### Étape 3 : Configuration MODE 1

```bash
# Copier template MODE 1
cp .env.mode1.example .env

# Éditer .env
nano .env
```

**Variables CRITIQUES à remplir** :

```bash
# ====== SÉCURITÉ ======
POSTGRES_PASSWORD=VotreMotDePasseSecuritéPostgres123!
REDIS_PASSWORD=VotreMotDePasseRedis456!
API_HMAC_SECRET=$(openssl rand -hex 32)
DASHBOARD_PASSWORD=VotreMotDePasseAdmin789!

# ====== PROXIES ======
# Oxylabs
OXYLABS_USER=votre_username_oxylabs
OXYLABS_PASS=votre_password_oxylabs

# SmartProxy
SMARTPROXY_USER=votre_username_smartproxy
SMARTPROXY_PASS=votre_password_smartproxy

# ====== MAILWIZZ ======
MAILWIZZ_SOS_EXPAT_API_KEY=votre_cle_api_sos_expat_ici
MAILWIZZ_ULIXAI_API_KEY=votre_cle_api_ulixai_ici

# ====== GOOGLE SEARCH ======
SERPAPI_KEY=votre_cle_serpapi
```

### Étape 4 : Lancement MODE 1

```bash
# Build containers
docker-compose build

# Lancer services
docker-compose up -d

# Vérifier logs
docker-compose logs -f scraper
```

### Étape 5 : Accès dashboard

```
URL : http://VOTRE_IP_VPS:8501
Password : (celui défini dans DASHBOARD_PASSWORD)
```

---

## 🟢 MODE 2 : Scraping Simple (sans proxies)

### Étape 1 : Connexion VPS

```bash
# Connexion SSH (même que MODE 1)
ssh root@VOTRE_IP_VPS

# Créer utilisateur scraper
adduser scraper
usermod -aG sudo,docker scraper

# Passer en utilisateur scraper
su - scraper
```

### Étape 2 : Clone du projet

```bash
# Créer dossier projets
mkdir -p ~/projets
cd ~/projets

# Clone repository
git clone https://github.com/votre-username/scraper-pro.git
cd scraper-pro
```

### Étape 3 : Configuration MODE 2

```bash
# Copier template MODE 2
cp .env.mode2.example .env

# Éditer .env
nano .env
```

**Variables CRITIQUES à remplir** :

```bash
# ====== MODE ======
SCRAPER_MODE=simple
ENABLE_PROXIES=false

# ====== SÉCURITÉ ======
POSTGRES_PASSWORD=VotreMotDePasseSecuritéPostgres123!
REDIS_PASSWORD=VotreMotDePasseRedis456!
API_HMAC_SECRET=$(openssl rand -hex 32)
DASHBOARD_PASSWORD=VotreMotDePasseAdmin789!

# ====== MAILWIZZ ======
MAILWIZZ_SOS_EXPAT_API_KEY=votre_cle_api_sos_expat_ici
MAILWIZZ_ULIXAI_API_KEY=votre_cle_api_ulixai_ici
```

**IMPORTANT** : Pas besoin de remplir les proxies, SerpAPI, ni 2Captcha en MODE 2.

### Étape 4 : Lancement MODE 2

```bash
# Utiliser docker-compose MODE simple
docker-compose -f docker-compose-mode-simple.yml build

# Lancer services
docker-compose -f docker-compose-mode-simple.yml up -d

# Vérifier logs
docker-compose -f docker-compose-mode-simple.yml logs -f scraper
```

### Étape 5 : Accès dashboard

```
URL : http://VOTRE_IP_VPS:8501
Password : (celui défini dans DASHBOARD_PASSWORD)
```

---

## ⚙️ Configuration

### Listes MailWizz (à créer avant)

#### SOS-Expat (10 listes)

| ID | Nom Liste | Catégorie |
|----|-----------|-----------|
| 1 | Avocats Internationaux | avocat |
| 2 | Assureurs Expatriés | assureur |
| 3 | Notaires Internationaux | notaire |
| 4 | Médecins Francophones | medecin |
| 5 | Comptables et Fiscalistes | comptable |
| 6 | Traducteurs et Interprètes | traducteur |
| 7 | Agents Immobiliers | agent_immo |
| 8 | Déménageurs Internationaux | demenageur |
| 9 | Banquiers et Conseillers | banquier |
| 11 | Consultants Expatriation | consultant |
| 10 | Contacts Divers | default |

#### Ulixai (4 listes)

| ID | Nom Liste | Catégorie |
|----|-----------|-----------|
| 1 | Blogueurs Voyage | blogueur |
| 2 | Influenceurs Réseaux Sociaux | influenceur |
| 3 | Admins Groupes Facebook | admin_groupe |
| 4 | YouTubeurs Voyage | youtubeur |
| 10 | Contacts Divers | default |

**Ajuster les IDs dans** : `config/mailwizz_routing.json`

### Firewall

```bash
# UFW (Ubuntu Firewall)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # API
sudo ufw allow 8501/tcp  # Dashboard
sudo ufw enable
```

### Reverse Proxy (Optionnel mais recommandé)

**Nginx pour HTTPS** :

```bash
sudo apt install nginx certbot python3-certbot-nginx

# Créer config Nginx
sudo nano /etc/nginx/sites-available/scraper-pro
```

```nginx
server {
    listen 80;
    server_name scraper.votredomaine.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Activer site
sudo ln -s /etc/nginx/sites-available/scraper-pro /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Obtenir certificat SSL
sudo certbot --nginx -d scraper.votredomaine.com
```

---

## 🚀 Lancement

### Commandes Docker Compose

**MODE 1** :
```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Redémarrer
docker-compose restart

# Rebuild après changement code
docker-compose up -d --build

# Logs
docker-compose logs -f scraper
docker-compose logs -f dashboard
```

**MODE 2** :
```bash
# Démarrer
docker-compose -f docker-compose-mode-simple.yml up -d

# Arrêter
docker-compose -f docker-compose-mode-simple.yml down

# Logs
docker-compose -f docker-compose-mode-simple.yml logs -f
```

### Démarrage automatique au boot

```bash
# Créer service systemd
sudo nano /etc/systemd/system/scraper-pro.service
```

**MODE 1** :
```ini
[Unit]
Description=Scraper-Pro MODE 1
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/scraper/projets/scraper-pro
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=scraper

[Install]
WantedBy=multi-user.target
```

**MODE 2** :
```ini
[Unit]
Description=Scraper-Pro MODE 2
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/scraper/projets/scraper-pro
ExecStart=/usr/local/bin/docker-compose -f docker-compose-mode-simple.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose-mode-simple.yml down
User=scraper

[Install]
WantedBy=multi-user.target
```

```bash
# Activer service
sudo systemctl enable scraper-pro
sudo systemctl start scraper-pro

# Vérifier status
sudo systemctl status scraper-pro
```

---

## ✅ Vérifications

### 1. Health checks

```bash
# PostgreSQL
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "SELECT 1"

# Redis
docker exec scraper_redis redis-cli -a VotreMotDePasseRedis ping

# API
curl http://localhost:8000/health

# Dashboard
curl http://localhost:8501
```

### 2. Test scraping job

1. **Accéder dashboard** : `http://VOTRE_IP:8501`
2. **Créer job test** : Onglet "📝 Créer Job"
   - Source : URLs personnalisées
   - URLs : 5-10 sites test
   - Catégorie : avocat
   - Platform : SOS-Expat
3. **Lancer** et surveiller progression
4. **Vérifier** : Onglet "📊 Jobs Actifs"

### 3. Vérifier pipeline complet

```bash
# 1. Contacts scrapés
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "SELECT COUNT(*) FROM scraped_contacts WHERE status='pending_validation'"

# 2. Contacts validés
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "SELECT COUNT(*) FROM validated_contacts WHERE status='ready_for_mailwizz'"

# 3. Contacts envoyés MailWizz
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "SELECT COUNT(*) FROM validated_contacts WHERE status='sent_to_mailwizz'"

# 4. Logs sync MailWizz
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "SELECT status, COUNT(*) FROM mailwizz_sync_log GROUP BY status"
```

---

## 💾 Backup & Monitoring

### Backup PostgreSQL automatique

```bash
# Créer script backup
mkdir -p ~/backups
nano ~/backups/backup-postgres.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/scraper/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER="scraper_postgres"
DB_NAME="scraper_db"
DB_USER="scraper_admin"

mkdir -p $BACKUP_DIR

# Backup
docker exec $CONTAINER pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_DIR/scraper_$TIMESTAMP.sql.gz"

# Garder seulement 7 derniers jours
find $BACKUP_DIR -name "scraper_*.sql.gz" -mtime +7 -delete

echo "Backup completed: scraper_$TIMESTAMP.sql.gz"
```

```bash
chmod +x ~/backups/backup-postgres.sh

# Cron job daily backup
crontab -e
```

Ajouter :
```
0 3 * * * /home/scraper/backups/backup-postgres.sh >> /home/scraper/backups/backup.log 2>&1
```

### Monitoring (optionnel)

**Prometheus + Grafana** :

```bash
# Ajouter au docker-compose.yml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
```

---

## 🔧 Troubleshooting

### Problème : Container scraper ne démarre pas

```bash
# Vérifier logs
docker-compose logs scraper

# Problèmes courants :
# 1. PostgreSQL pas prêt → Attendre 30sec et retry
# 2. .env mal configuré → Vérifier variables
# 3. Port 8000 déjà utilisé → Changer port dans docker-compose.yml
```

### Problème : Dashboard ne charge pas

```bash
# Vérifier dashboard logs
docker-compose logs dashboard

# Vérifier API accessible
curl http://localhost:8000/health

# Redémarrer dashboard
docker-compose restart dashboard
```

### Problème : Proxies bloqués (MODE 1)

```bash
# Vérifier stats proxies
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "SELECT status, COUNT(*) FROM proxy_stats GROUP BY status"

# Réinitialiser proxy en cooldown
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "UPDATE proxy_stats SET status='ACTIVE', consecutive_failures=0, cooldown_until=NULL WHERE status='COOLDOWN'"
```

### Problème : MailWizz sync échoue

```bash
# Vérifier logs sync
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "SELECT * FROM mailwizz_sync_log WHERE status='failed' ORDER BY synced_at DESC LIMIT 10"

# Tester connexion MailWizz
docker exec scraper_app python -c "
from scraper.integrations.mailwizz_client import get_client
client = get_client('sos-expat')
print(client.api_url, client.api_key[:10])
"

# Re-envoyer contacts failed
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "UPDATE validated_contacts SET status='ready_for_mailwizz', retry_count=0 WHERE status='failed'"
```

### Problème : Job scraping bloqué

```bash
# Vérifier jobs en cours
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "SELECT id, name, status, progress FROM scraping_jobs WHERE status='running'"

# Reset job bloqué
docker exec scraper_postgres psql -U scraper_admin -d scraper_db -c "UPDATE scraping_jobs SET status='failed' WHERE id=X"  # Remplacer X par l'ID
```

---

## 📞 Support

**Problèmes techniques** :
- 📧 Email : support@sos-expat.com
- 📝 GitHub Issues : https://github.com/votre-repo/scraper-pro/issues

**Documentation** :
- 📖 User Guide : `USER_GUIDE.md`
- 🔧 API Docs : `http://VOTRE_IP:8000/docs` (FastAPI auto-doc)

---

## ✅ Checklist post-déploiement

- [ ] VPS configuré (Docker + Docker Compose installés)
- [ ] `.env` rempli avec toutes les clés API
- [ ] Firewall configuré (ports 22, 8000, 8501)
- [ ] Services démarrés (`docker-compose up -d`)
- [ ] Health checks OK (Postgres, Redis, API)
- [ ] Dashboard accessible (http://IP:8501)
- [ ] Job test créé et exécuté avec succès
- [ ] Contacts validés et envoyés vers MailWizz
- [ ] Backup PostgreSQL automatique configuré
- [ ] Service systemd activé pour auto-start
- [ ] (Optionnel) Reverse proxy Nginx + SSL
- [ ] (Optionnel) Monitoring Prometheus + Grafana

---

**Version** : 1.0.0
**Date** : Février 2026
**Auteur** : Williams - SOS-Expat.com / Ulixai.com
