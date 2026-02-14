# 🚀 GUIDE DE DÉPLOIEMENT PRODUCTION - SCRAPER-PRO

**Le guide ultime, étape par étape, pour déployer Scraper-Pro en production sans erreur possible.**

> Ce guide est conçu pour être utilisable par un **débutant complet**. Chaque commande est expliquée, testée, et copy-paste ready.

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble](#-1-vue-densemble)
2. [Prérequis et Budget](#-2-prérequis-et-budget)
3. [Achat et Configuration VPS Hetzner](#-3-achat-et-configuration-vps-hetzner)
4. [Installation Automatique (RECOMMANDÉ)](#-4-installation-automatique-recommandé)
5. [Installation Manuelle (Step by Step)](#-5-installation-manuelle-step-by-step)
6. [Configuration Initiale](#-6-configuration-initiale)
7. [Accès et Tests](#-7-accès-et-tests)
8. [Monitoring et Grafana](#-8-monitoring-et-grafana)
9. [Maintenance et Backups](#-9-maintenance-et-backups)
10. [Migration vers Google (Plus tard)](#-10-migration-vers-google-plus-tard)
11. [Rollback en Cas de Problème](#-11-rollback-en-cas-de-problème)
12. [Troubleshooting](#-12-troubleshooting)
13. [Checklist Finale](#-13-checklist-finale)

---

## 🎯 1. VUE D'ENSEMBLE

### Ce que vous allez déployer

**Scraper-Pro** est un système professionnel de scraping B2B avec :
- 🔗 **Scraping d'URLs personnalisées** (mode URLs Only - SANS proxies, SANS Google)
- 📧 **Validation automatique** des emails et téléphones
- 🎯 **Catégorisation intelligente** (14 catégories professionnelles)
- 📊 **Dashboard Premium** Streamlit pour gérer tout en 1 clic
- 🔄 **Injection MailWizz** automatique vers vos listes emails
- 📈 **Monitoring complet** Grafana + Prometheus

### Architecture finale

```
┌─────────────────────────────────────────────────────────┐
│         Serveur Hetzner CPX31 (8GB RAM, 4 vCPU)        │
├─────────────────────────────────────────────────────────┤
│  🌐 Nginx (Reverse Proxy + SSL)                        │
│    ├─ dashboard.votredomaine.com → Streamlit (8501)   │
│    ├─ api.votredomaine.com → FastAPI (8000)           │
│    └─ grafana.votredomaine.com → Grafana (3000)       │
├─────────────────────────────────────────────────────────┤
│  🐳 Docker Containers                                   │
│    ├─ scraper-postgres (PostgreSQL 16)                │
│    ├─ scraper-redis (Redis 7)                         │
│    ├─ scraper-app (FastAPI + Scrapy)                  │
│    ├─ scraper-dashboard (Streamlit)                   │
│    ├─ scraper-prometheus (Metrics)                    │
│    ├─ scraper-grafana (Monitoring)                    │
│    ├─ scraper-loki (Logs)                             │
│    └─ scraper-promtail (Log shipping)                 │
└─────────────────────────────────────────────────────────┘
```

### Timeline complète

| Étape | Durée | Difficulté |
|-------|-------|------------|
| Achat VPS Hetzner | 5 min | ⭐ Facile |
| Premier accès SSH | 5 min | ⭐ Facile |
| Installation automatique | 10 min | ⭐ Facile |
| Configuration .env | 10 min | ⭐⭐ Moyen |
| Démarrage services | 5 min | ⭐ Facile |
| Configuration Nginx + SSL | 15 min | ⭐⭐ Moyen |
| Tests et validation | 10 min | ⭐ Facile |
| **TOTAL** | **1h environ** | |

---

## 💰 2. PRÉREQUIS ET BUDGET

### Compétences requises

- ✅ Utiliser un terminal SSH (on vous guide)
- ✅ Copier-coller des commandes
- ✅ Éditer un fichier texte
- ❌ PAS besoin de connaître Docker, Linux, ou le code

### Budget mensuel

#### Mode URLs Only (recommandé pour démarrer)

| Service | Coût/mois | Obligatoire |
|---------|-----------|-------------|
| 🖥️ Hetzner CPX31 (4 vCPU, 8GB RAM) | ~13€ | ✅ OUI |
| 🌐 Nom de domaine (optionnel) | ~10€/an | ❌ Optionnel |
| 📧 MailWizz (si vous l'avez déjà) | Variable | ⚠️ Optionnel |
| **TOTAL** | **~13€/mois** | |

#### Mode Full (Google Search + Maps)

| Service | Coût/mois | Obligatoire |
|---------|-----------|-------------|
| 🖥️ Hetzner CPX31 | ~13€ | ✅ OUI |
| 🔐 Proxies (SmartProxy, Oxylabs, BrightData) | 500-2000€ | ✅ OUI |
| 🔎 SerpAPI (fallback anti-CAPTCHA) | 50-200€ | ✅ OUI |
| 🌐 Nom de domaine | ~10€/an | ❌ Optionnel |
| **TOTAL** | **~563-2213€/mois** | |

> **💡 Recommandation** : Commencez avec le **Mode URLs Only** (13€/mois) pour tester le système sans risque. Vous pourrez activer Google plus tard en 5 minutes.

### Ce dont vous avez besoin

- ✅ Une carte bancaire (pour Hetzner)
- ✅ Une adresse email
- ✅ Un ordinateur avec accès SSH (Windows, Mac, Linux)
- ✅ 1 heure de temps devant vous

---

## 🛒 3. ACHAT ET CONFIGURATION VPS HETZNER

### Étape 1 : Créer un compte Hetzner

1. Aller sur **https://www.hetzner.com/**
2. Cliquer **"Sign Up"** (en haut à droite)
3. Remplir le formulaire :
   - Email
   - Mot de passe
   - Adresse (obligatoire pour facturation)
4. Confirmer l'email reçu
5. Ajouter un moyen de paiement (CB ou PayPal)

### Étape 2 : Commander le serveur CPX31

1. Se connecter à **https://console.hetzner.cloud/**
2. Cliquer **"New Project"**
   - Nom : `scraper-pro-production`
3. Cliquer **"Add Server"**
4. Sélectionner :
   - **Location** : `Nuremberg` (Allemagne) ou `Helsinki` (Finlande)
   - **Image** : `Ubuntu 22.04`
   - **Type** : `CPX31` (4 vCPU, 8GB RAM, 160GB SSD)
   - **SSH Key** : Cliquer "Add SSH Key" (voir ci-dessous)
   - **Hostname** : `scraper-pro`
5. Cliquer **"Create & Buy Now"**

> **💡 Astuce** : Le serveur CPX31 coûte environ 13€/mois. Hetzner facture à l'heure (environ 0,018€/heure), vous pouvez donc le supprimer quand vous voulez sans engagement.

### Étape 3 : Générer une clé SSH (si vous n'en avez pas)

#### Sur Windows (avec Git Bash ou PowerShell)

```bash
# Ouvrir Git Bash ou PowerShell
ssh-keygen -t ed25519 -C "votre-email@example.com"

# Appuyer sur Entrée 3 fois (pas de passphrase pour simplifier)
# La clé est créée dans : C:\Users\VotreNom\.ssh\id_ed25519.pub

# Afficher la clé publique
cat ~/.ssh/id_ed25519.pub
```

#### Sur Mac / Linux

```bash
# Ouvrir Terminal
ssh-keygen -t ed25519 -C "votre-email@example.com"

# Appuyer sur Entrée 3 fois
# La clé est créée dans : ~/.ssh/id_ed25519.pub

# Afficher la clé publique
cat ~/.ssh/id_ed25519.pub
```

**Copier toute la ligne affichée** (commence par `ssh-ed25519 ...`) et la coller dans Hetzner → Add SSH Key.

### Étape 4 : Configurer le Firewall Hetzner

1. Dans le Cloud Console, aller dans **"Firewalls"**
2. Cliquer **"Create Firewall"**
3. Nom : `scraper-firewall`
4. Règles entrantes :
   - ✅ SSH (port 22) : `0.0.0.0/0` (tout le monde)
   - ✅ HTTP (port 80) : `0.0.0.0/0`
   - ✅ HTTPS (port 443) : `0.0.0.0/0`
5. Règles sortantes :
   - ✅ Tout autoriser
6. Cliquer **"Create"**
7. Attacher le firewall au serveur `scraper-pro`

### Étape 5 : Premier accès SSH

Une fois le serveur créé (environ 30 secondes), vous verrez son **adresse IP publique** (exemple : `95.217.123.45`).

```bash
# Remplacer par VOTRE adresse IP
ssh root@95.217.123.45
```

**À la première connexion**, vous verrez ce message :

```
The authenticity of host '95.217.123.45' can't be established.
Are you sure you want to continue connecting (yes/no)?
```

Tapez **`yes`** puis Entrée.

✅ **Vous êtes maintenant connecté au serveur !**

---

## ⚡ 4. INSTALLATION AUTOMATIQUE (RECOMMANDÉ)

### Option A : Script d'installation one-liner

Cette méthode installe **tout automatiquement** en une seule commande.

```bash
# Copier-coller cette commande (une seule ligne)
curl -fsSL https://raw.githubusercontent.com/VOTRE_ORG/scraper-pro/main/scripts/quick_install.sh | bash
```

> **⚠️ ATTENTION** : Si vous n'avez pas de script `quick_install.sh` dans votre repo, passez à l'**Option B** ci-dessous.

### Ce que le script fait automatiquement

1. ✅ Met à jour Ubuntu
2. ✅ Installe Docker + Docker Compose
3. ✅ Installe Git, Nginx, Certbot
4. ✅ Clone le repository scraper-pro
5. ✅ Copie `.env.production` vers `.env`
6. ✅ Génère des secrets forts automatiquement
7. ✅ Build les images Docker
8. ✅ Démarre tous les services
9. ✅ Configure le firewall UFW

### Validation

```bash
# Vérifier que les containers tournent
docker ps

# Vous devriez voir 8 containers :
# - scraper-postgres
# - scraper-redis
# - scraper-app
# - scraper-dashboard
# - scraper-prometheus
# - scraper-grafana
# - scraper-loki
# - scraper-promtail
```

✅ **Si vous voyez 8 containers "Up", passez directement à [Configuration Initiale](#-6-configuration-initiale).**

---

## 🛠️ 5. INSTALLATION MANUELLE (STEP BY STEP)

Si le script automatique ne fonctionne pas, ou si vous préférez tout contrôler, suivez ces étapes.

### Étape 1 : Mise à jour du système

```bash
# Se connecter en SSH (si pas déjà fait)
ssh root@95.217.123.45

# Mettre à jour tous les paquets
apt update && apt upgrade -y

# Rebooter (recommandé)
reboot

# Attendre 1 minute, puis se reconnecter
ssh root@95.217.123.45
```

### Étape 2 : Installer Docker

```bash
# Installer les dépendances
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Ajouter la clé GPG Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Ajouter le repository Docker
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Mettre à jour et installer Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io

# Vérifier l'installation
docker --version
# Résultat attendu : Docker version 24.0.x ou supérieur
```

### Étape 3 : Installer Docker Compose

```bash
# Télécharger Docker Compose (dernière version)
curl -L "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Rendre exécutable
chmod +x /usr/local/bin/docker-compose

# Vérifier l'installation
docker-compose --version
# Résultat attendu : Docker Compose version v2.24.5 ou supérieur
```

### Étape 4 : Installer Git, Nginx, et outils

```bash
# Installer Git
apt install -y git

# Installer Nginx (reverse proxy)
apt install -y nginx

# Installer Certbot (SSL/TLS gratuit)
apt install -y certbot python3-certbot-nginx

# Installer des outils utiles
apt install -y htop curl wget nano

# Vérifier
git --version
nginx -v
certbot --version
```

### Étape 5 : Configurer le firewall UFW

```bash
# Installer UFW (si pas déjà installé)
apt install -y ufw

# Autoriser SSH (IMPORTANT : avant d'activer UFW)
ufw allow 22/tcp

# Autoriser HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Activer UFW
ufw enable

# Vérifier le statut
ufw status

# Résultat attendu :
# Status: active
# To                         Action      From
# --                         ------      ----
# 22/tcp                     ALLOW       Anywhere
# 80/tcp                     ALLOW       Anywhere
# 443/tcp                    ALLOW       Anywhere
```

### Étape 6 : Cloner le repository

```bash
# Créer le répertoire de déploiement
mkdir -p /opt/scraper-pro
cd /opt/scraper-pro

# Cloner le projet (remplacer par VOTRE URL)
git clone https://github.com/VOTRE_ORG/scraper-pro.git .

# Vérifier
ls -la
# Vous devriez voir : docker-compose.production.yml, .env.production, etc.
```

### Étape 7 : Configurer les variables d'environnement

```bash
# Copier le fichier exemple
cp .env.production .env

# Éditer le fichier
nano .env
```

#### Variables OBLIGATOIRES à modifier

Utilisez les flèches du clavier pour naviguer, puis modifiez ces lignes :

```bash
# ========================================
# PASSWORDS (OBLIGATOIRE)
# ========================================

# PostgreSQL
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD_32_CHARS_MIN

# Redis
REDIS_PASSWORD=CHANGE_ME_STRONG_PASSWORD_32_CHARS_MIN

# Dashboard
DASHBOARD_PASSWORD=CHANGE_ME_STRONG_PASSWORD

# API HMAC Secret (64 caractères minimum)
API_HMAC_SECRET=CHANGE_ME_STRONG_SECRET_64_CHARS_HERE

# Grafana
GRAFANA_PASSWORD=CHANGE_ME_GRAFANA_PASSWORD

# ========================================
# MAILWIZZ (Optionnel si vous l'avez)
# ========================================

MAILWIZZ_SOS_EXPAT_API_KEY=your_api_key_here
MAILWIZZ_ULIXAI_API_KEY=your_api_key_here

# ========================================
# WEBHOOKS (Optionnel)
# ========================================

WEBHOOK_SOS_EXPAT_SECRET=your_hmac_secret_here
WEBHOOK_ULIXAI_SECRET=your_hmac_secret_here
```

#### Générer des secrets forts

**Option 1 : Commandes rapides**

```bash
# PostgreSQL password (copier le résultat dans .env)
openssl rand -base64 32

# Redis password
openssl rand -base64 32

# API HMAC secret (64 caractères)
openssl rand -hex 32

# Dashboard password
openssl rand -base64 24

# Grafana password
openssl rand -base64 24
```

**Option 2 : Générateur en ligne**

Allez sur **https://passwordsgenerator.net/** et générez des mots de passe de 32+ caractères.

#### Sauvegarder et quitter nano

1. Appuyez sur **Ctrl + O** (pour sauvegarder)
2. Appuyez sur **Entrée** (confirmer le nom)
3. Appuyez sur **Ctrl + X** (pour quitter)

#### Protéger le fichier .env

```bash
# Le fichier .env contient des secrets, personne d'autre ne doit le lire
chmod 600 .env

# Vérifier
ls -la .env
# Résultat attendu : -rw------- (seulement vous pouvez lire/écrire)
```

### Étape 8 : Build et démarrer les services

```bash
# Build toutes les images Docker (peut prendre 5-10 minutes)
docker-compose -f docker-compose.production.yml build

# Démarrer tous les services en arrière-plan
docker-compose -f docker-compose.production.yml up -d

# Vérifier que les containers démarrent
docker-compose -f docker-compose.production.yml ps

# Résultat attendu : 8 containers avec "Up" dans la colonne STATE
```

### Étape 9 : Vérifier les logs

```bash
# Voir les logs de tous les services en temps réel
docker-compose -f docker-compose.production.yml logs -f

# Appuyez sur Ctrl+C pour arrêter de suivre les logs

# Voir les logs d'un service spécifique
docker logs scraper-app --tail 50
docker logs scraper-postgres --tail 50
docker logs scraper-dashboard --tail 50
```

**⚠️ Erreurs courantes :**

- Si vous voyez `connection refused` : attendez 30 secondes que PostgreSQL démarre complètement
- Si vous voyez `password authentication failed` : vérifiez que `POSTGRES_PASSWORD` est identique partout dans `.env`
- Si vous voyez `port already in use` : un autre service utilise le port, changez-le dans `docker-compose.production.yml`

✅ **Si aucune erreur, passez à la configuration initiale !**

---

## ⚙️ 6. CONFIGURATION INITIALE

### Étape 1 : Tester l'API

```bash
# Health check de l'API
curl http://localhost:8000/health

# Résultat attendu :
# {"status":"ok","service":"scraper-pro","postgres":true,"redis":true}
```

✅ **Si vous voyez `"status":"ok"`, l'API fonctionne !**

### Étape 2 : Tester PostgreSQL

```bash
# Se connecter à PostgreSQL
docker exec -it scraper-postgres psql -U scraper_admin -d scraper_db

# Une fois connecté, vérifier les tables
\dt

# Résultat attendu : vous devez voir ces tables :
# - scraping_jobs
# - scraped_contacts
# - validated_contacts
# - url_deduplication_cache
# - content_hash_cache
# - mailwizz_sync_log
# - error_logs
# - whois_cache
# - scraped_articles

# Quitter PostgreSQL
\q
```

### Étape 3 : Tester Redis

```bash
# Se connecter à Redis (remplacer YOUR_REDIS_PASSWORD par le vrai mot de passe depuis .env)
docker exec -it scraper-redis redis-cli -a YOUR_REDIS_PASSWORD

# Une fois connecté, tester
PING

# Résultat attendu : PONG

# Voir toutes les clés (vide au début)
KEYS *

# Quitter Redis
exit
```

### Étape 4 : Accéder au Dashboard (test local)

Pour l'instant, le Dashboard n'est accessible que depuis le serveur (localhost). Nous allons configurer Nginx pour y accéder depuis votre navigateur.

```bash
# Test rapide (depuis le serveur)
curl -I http://localhost:8501

# Résultat attendu : HTTP/1.1 200 OK
```

---

## 🌐 7. ACCÈS ET TESTS

### Configuration Nginx (Reverse Proxy + SSL)

#### Option A : Avec un nom de domaine (RECOMMANDÉ)

Si vous avez un nom de domaine (exemple : `example.com`), vous pouvez créer 3 sous-domaines :

- **dashboard.example.com** → Dashboard Streamlit
- **api.example.com** → API FastAPI
- **grafana.example.com** → Monitoring Grafana

**Étape 1 : Configurer les DNS**

Chez votre registrar (OVH, Gandi, Namecheap, etc.), créez 3 enregistrements DNS de type **A** :

| Nom | Type | Valeur |
|-----|------|--------|
| dashboard | A | 95.217.123.45 (votre IP serveur) |
| api | A | 95.217.123.45 |
| grafana | A | 95.217.123.45 |

**Attendre 5-10 minutes** que les DNS se propagent.

**Étape 2 : Configuration Nginx pour le Dashboard**

```bash
# Créer le fichier de configuration
nano /etc/nginx/sites-available/scraper-dashboard
```

Copier-coller ce contenu (remplacer `dashboard.example.com` par VOTRE domaine) :

```nginx
server {
    listen 80;
    server_name dashboard.example.com;

    location / {
        proxy_pass http://localhost:8501;
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
```

Sauvegarder (**Ctrl+O**, **Entrée**, **Ctrl+X**).

**Étape 3 : Configuration Nginx pour l'API**

```bash
nano /etc/nginx/sites-available/scraper-api
```

Copier-coller ce contenu (remplacer `api.example.com`) :

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Sauvegarder.

**Étape 4 : Configuration Nginx pour Grafana**

```bash
nano /etc/nginx/sites-available/scraper-grafana
```

Copier-coller ce contenu (remplacer `grafana.example.com`) :

```nginx
server {
    listen 80;
    server_name grafana.example.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Sauvegarder.

**Étape 5 : Activer les sites**

```bash
# Créer les liens symboliques
ln -s /etc/nginx/sites-available/scraper-dashboard /etc/nginx/sites-enabled/
ln -s /etc/nginx/sites-available/scraper-api /etc/nginx/sites-enabled/
ln -s /etc/nginx/sites-available/scraper-grafana /etc/nginx/sites-enabled/

# Tester la configuration
nginx -t

# Résultat attendu : syntax is ok, test is successful

# Recharger Nginx
systemctl reload nginx
```

**Étape 6 : Installer les certificats SSL (Let's Encrypt)**

```bash
# Dashboard
certbot --nginx -d dashboard.example.com

# Répondre aux questions :
# - Email : votre email
# - Terms of service : A (agree)
# - Share email : N (no)
# - Redirect HTTP to HTTPS : 2 (yes)

# API
certbot --nginx -d api.example.com

# Grafana
certbot --nginx -d grafana.example.com
```

Les certificats SSL sont installés et se renouvellent automatiquement !

**Étape 7 : Configuration du renouvellement automatique**

```bash
# Tester le renouvellement automatique
certbot renew --dry-run

# Résultat attendu : Congratulations, all simulated renewals succeeded

# Ajouter un cron job pour renouveler automatiquement
crontab -e

# Ajouter cette ligne à la fin :
0 3 * * * certbot renew --quiet
```

Sauvegarder (**Ctrl+O**, **Entrée**, **Ctrl+X**).

✅ **Maintenant, vous pouvez accéder à :**
- **https://dashboard.example.com** (Dashboard Premium)
- **https://api.example.com** (API)
- **https://grafana.example.com** (Monitoring)

#### Option B : Sans nom de domaine (accès par IP)

Si vous n'avez pas de domaine, vous pouvez accéder directement par IP, mais **SANS SSL** (non sécurisé).

```bash
# Modifier le firewall pour exposer les ports
ufw allow 8501/tcp  # Dashboard
ufw allow 8000/tcp  # API
ufw allow 3000/tcp  # Grafana
```

✅ **Accès :**
- **http://95.217.123.45:8501** (Dashboard)
- **http://95.217.123.45:8000** (API)
- **http://95.217.123.45:3000** (Grafana)

> **⚠️ ATTENTION** : Cette méthode est **NON SÉCURISÉE** (pas de SSL). Utilisez-la uniquement pour les tests, jamais en production avec de vraies données.

### Accès au Dashboard

1. Ouvrir **https://dashboard.example.com** (ou http://IP:8501)
2. Vous verrez un écran de login avec un champ **"Password"**
3. Entrer le mot de passe depuis `.env` → `DASHBOARD_PASSWORD`
4. Cliquer **"Login"**

✅ **Vous êtes connecté au Dashboard Premium !**

### Premier test : Créer un job de scraping

1. Dans le Dashboard, aller dans l'onglet **"Scraping URLs (Actif)"**
2. Section **"Lancer un Nouveau Job"**
3. Remplir :
   - **Nom du job** : `Test Job 1`
   - **Plateforme** : `sos-expat`
   - **URLs** : Coller quelques URLs de test (une par ligne) :
     ```
     https://example.com
     https://www.wikipedia.org
     https://www.github.com
     ```
4. Cliquer **"Lancer le Job"**

**Résultat attendu** : Le job démarre, et vous voyez :
- Un ID de job (exemple : `#123`)
- Statut : `running`
- Progression en temps réel

5. Attendre 1-2 minutes que le job se termine
6. Vérifier les résultats dans l'onglet **"Contacts"**

✅ **Si vous voyez des contacts extraits, le système fonctionne parfaitement !**

---

## 📊 8. MONITORING ET GRAFANA

### Accès à Grafana

1. Ouvrir **https://grafana.example.com** (ou http://IP:3000)
2. Login :
   - **Username** : `admin`
   - **Password** : Depuis `.env` → `GRAFANA_PASSWORD`
3. Cliquer **"Log in"**

### Dashboards disponibles

Grafana a été configuré avec plusieurs dashboards pré-installés :

1. **Scraper Overview** : Vue d'ensemble du système
   - Jobs en cours
   - Contacts scrapés (total)
   - Contacts validés
   - Taux de succès
   - Erreurs récentes

2. **Deduplication Stats** : Statistiques de déduplication
   - URLs dédupliquées (exact + normalized)
   - Emails uniques
   - Content hash uniques
   - Taux de déduplication global

3. **PostgreSQL Performance** : Métriques de la base de données
   - Connections actives
   - Slow queries
   - Index usage
   - Table sizes

4. **Redis Performance** : Métriques Redis
   - Memory usage
   - Hit rate
   - Commands per second
   - Connected clients

5. **System Resources** : Ressources du serveur
   - CPU usage
   - RAM usage
   - Disk I/O
   - Network traffic

### Configuration des alertes email

1. Dans Grafana, aller dans **"Alerting"** → **"Contact points"**
2. Cliquer **"New contact point"**
3. Remplir :
   - **Name** : `Email Alerts`
   - **Type** : `Email`
   - **Addresses** : `votre-email@example.com`
4. Cliquer **"Test"** pour vérifier que l'email arrive
5. Cliquer **"Save contact point"**

Les alertes configurées :
- ✅ Service down (critical)
- ✅ High job failure rate (warning)
- ✅ PostgreSQL connection issues (warning)
- ✅ Redis connection issues (warning)
- ✅ Disk usage > 80% (warning)

---

## 🔧 9. MAINTENANCE ET BACKUPS

### Backup automatique de PostgreSQL

**Étape 1 : Créer le script de backup**

```bash
# Créer le répertoire de backups
mkdir -p /home/scraper/backups

# Créer le script
nano /home/scraper/backup-postgres.sh
```

Copier-coller ce contenu :

```bash
#!/bin/bash

# Configuration
BACKUP_DIR="/home/scraper/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
POSTGRES_PASSWORD="YOUR_POSTGRES_PASSWORD"  # Remplacer par le vrai mot de passe
CONTAINER_NAME="scraper-postgres"
DB_USER="scraper_admin"
DB_NAME="scraper_db"

# Créer le répertoire si nécessaire
mkdir -p $BACKUP_DIR

# Exécuter le backup
docker exec $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/scraper_db_$TIMESTAMP.sql.gz

# Vérifier que le backup a réussi
if [ $? -eq 0 ]; then
    echo "✅ Backup réussi : scraper_db_$TIMESTAMP.sql.gz"
else
    echo "❌ Backup échoué"
    exit 1
fi

# Garder seulement les 7 derniers backups (1 semaine)
find $BACKUP_DIR -name "scraper_db_*.sql.gz" -mtime +7 -delete

# Afficher l'espace utilisé
du -sh $BACKUP_DIR

echo "✅ Backup terminé avec succès"
```

**Étape 2 : Rendre le script exécutable**

```bash
chmod +x /home/scraper/backup-postgres.sh
```

**Étape 3 : Tester le script**

```bash
# Lancer manuellement
/home/scraper/backup-postgres.sh

# Vérifier que le backup a été créé
ls -lh /home/scraper/backups/

# Vous devriez voir un fichier .sql.gz
```

**Étape 4 : Configurer le cron (backup quotidien à 2h du matin)**

```bash
# Éditer le crontab
crontab -e

# Ajouter cette ligne à la fin :
0 2 * * * /home/scraper/backup-postgres.sh >> /home/scraper/backup.log 2>&1
```

Sauvegarder (**Ctrl+O**, **Entrée**, **Ctrl+X**).

✅ **Les backups se feront automatiquement tous les jours à 2h du matin !**

### Restaurer un backup

Si vous avez besoin de restaurer un backup :

```bash
# Arrêter les services
docker-compose -f docker-compose.production.yml down

# Lister les backups disponibles
ls -lh /home/scraper/backups/

# Choisir un backup (exemple : scraper_db_20260213_020000.sql.gz)
gunzip < /home/scraper/backups/scraper_db_20260213_020000.sql.gz | docker-compose -f docker-compose.production.yml run --rm postgres psql -U scraper_admin -d scraper_db

# Redémarrer les services
docker-compose -f docker-compose.production.yml up -d
```

### Rotation des logs Docker

Les logs Docker sont automatiquement limités dans `docker-compose.production.yml` :

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"    # Maximum 50MB par fichier de log
    max-file: "3"      # Garder 3 fichiers (= 150MB max)
```

Pour nettoyer manuellement :

```bash
# Voir l'espace utilisé par Docker
docker system df

# Nettoyer les logs et images non utilisées
docker system prune -a --volumes
```

### Mise à jour du système

**Tous les mois**, pensez à mettre à jour le système :

```bash
# Se connecter au serveur
ssh root@95.217.123.45

# Mettre à jour les paquets
apt update && apt upgrade -y

# Nettoyer
apt autoremove -y

# Rebooter (recommandé)
reboot
```

### Mise à jour de Scraper-Pro

Quand une nouvelle version est disponible :

```bash
# Aller dans le répertoire du projet
cd /opt/scraper-pro

# Sauvegarder le .env actuel
cp .env .env.backup

# Pull les dernières modifications
git pull origin main

# Rebuild les images
docker-compose -f docker-compose.production.yml build

# Restart
docker-compose -f docker-compose.production.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.production.yml logs -f
```

---

## 🚀 10. MIGRATION VERS GOOGLE (PLUS TARD)

Quand vous serez prêt à activer **Google Search** et **Google Maps**, voici comment faire.

### Étape 1 : Souscrire aux services

#### Proxies (choisir UN seul provider)

**Option A : SmartProxy** (recommandé, bon rapport qualité/prix)
- Site : **https://smartproxy.com/**
- Prix : ~500-800€/mois (10GB de data)
- Type : Residential proxies
- Setup : Très simple

**Option B : Oxylabs** (qualité premium)
- Site : **https://oxylabs.io/**
- Prix : ~1000-2000€/mois
- Type : Datacenter ou Residential
- Setup : Moyen

**Option C : BrightData** (anciennement Luminati)
- Site : **https://brightdata.com/**
- Prix : ~600-1500€/mois
- Type : Residential proxies
- Setup : Complexe mais très puissant

#### SerpAPI (fallback anti-CAPTCHA Google)

- Site : **https://serpapi.com/**
- Prix : ~50-200€/mois (5000-50000 requêtes)
- Setup : Très simple (juste une clé API)

### Étape 2 : Configurer .env

```bash
# Se connecter au serveur
ssh root@95.217.123.45

# Éditer .env
cd /opt/scraper-pro
nano .env
```

Modifier ces lignes :

```bash
# ========================================
# MODE DE SCRAPING
# ========================================

# Passer de "urls_only" à "full"
SCRAPING_MODE=full

# ========================================
# PROXY PROVIDER
# ========================================

# Choisir votre provider (oxylabs, brightdata, smartproxy)
PROXY_PROVIDER=smartproxy

# Vos credentials proxy
PROXY_USER=your_username_here
PROXY_PASS=your_password_here

# ========================================
# SERPAPI (GOOGLE SEARCH FALLBACK)
# ========================================

SERPAPI_KEY=your_serpapi_key_here
```

Sauvegarder (**Ctrl+O**, **Entrée**, **Ctrl+X**).

### Étape 3 : Redémarrer les services

```bash
# Arrêter les services
docker-compose -f docker-compose.production.yml down

# Redémarrer
docker-compose -f docker-compose.production.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.production.yml logs -f scraper-app
```

### Étape 4 : Tester Google Search

1. Aller sur le **Dashboard**
2. Vous verrez maintenant un nouvel onglet : **"Scraping Google"**
3. Créer un job **"Google Search"** :
   - **Query** : `avocat Paris`
   - **Max results** : `50`
   - **Country** : `fr`
   - **Category** : `avocat`
   - **Platform** : `sos-expat`
4. Cliquer **"Lancer le Job"**
5. Surveiller les logs :
   ```bash
   docker logs scraper-app -f
   ```

**Si vous voyez des résultats Google dans l'onglet Contacts, c'est réussi !**

---

## 🔄 11. ROLLBACK EN CAS DE PROBLÈME

Cette section décrit comment revenir en arrière si quelque chose ne fonctionne pas.

### Arrêter les Services (Réversible)

Cette méthode arrête tous les containers mais **préserve vos données** (PostgreSQL, Redis).

```bash
# Se connecter au serveur
ssh root@95.217.123.45

# Aller dans le répertoire du projet
cd /opt/scraper-pro

# Arrêter tous les services
docker-compose -f docker-compose.production.yml down

# Résultat : Les containers sont arrêtés, mais les volumes persistent
```

**Pour redémarrer après :**

```bash
# Redémarrer tous les services
docker-compose -f docker-compose.production.yml up -d

# Vérifier
docker ps
```

✅ **Vos données (jobs, contacts, cache) sont toujours là !**

---

### Redémarrer un Service Spécifique

Si un seul service pose problème :

```bash
# Redémarrer l'API
docker restart scraper-app

# Redémarrer PostgreSQL
docker restart scraper-postgres

# Redémarrer Redis
docker restart scraper-redis

# Redémarrer le Dashboard
docker restart scraper-dashboard

# Redémarrer Grafana
docker restart scraper-grafana
```

---

### Supprimer Complètement (DESTRUCTIF)

⚠️ **ATTENTION : Cette méthode supprime TOUTES les données (base de données, cache, logs).**

```bash
# Arrêter et supprimer TOUS les containers + volumes
docker-compose -f docker-compose.production.yml down -v

# Nettoyer tout Docker (images, volumes orphelins, etc.)
docker system prune -a --volumes -f

# Résultat : Le système est complètement réinitialisé
```

**Utilisez cette méthode UNIQUEMENT si :**
- Vous voulez recommencer de zéro
- Vous avez un backup récent
- Vous êtes sûr de ne pas avoir besoin des données

---

### Restaurer depuis un Backup

Si vous avez un backup PostgreSQL (créé avec le script de backup) :

```bash
# Lister les backups disponibles
ls -lh /home/scraper/backups/

# Vous verrez des fichiers comme : scraper_db_20260213_020000.sql.gz

# Étape 1 : Arrêter les services
cd /opt/scraper-pro
docker-compose -f docker-compose.production.yml down

# Étape 2 : Supprimer les anciennes données PostgreSQL
docker volume rm scraper-pro_postgres_data

# Étape 3 : Redémarrer PostgreSQL seul
docker-compose -f docker-compose.production.yml up -d postgres

# Attendre 10 secondes que PostgreSQL soit prêt
sleep 10

# Étape 4 : Restaurer le backup (remplacer par le vrai nom de fichier)
gunzip < /home/scraper/backups/scraper_db_20260213_020000.sql.gz | \
    docker exec -i scraper-postgres psql -U scraper_admin -d scraper_db

# Étape 5 : Redémarrer tous les services
docker-compose -f docker-compose.production.yml up -d

# Étape 6 : Vérifier
docker ps
curl http://localhost:8000/health
```

✅ **Vos données sont restaurées à l'état du backup !**

---

### Revenir à une Version Précédente du Code

Si une mise à jour du code a cassé quelque chose :

```bash
# Aller dans le répertoire
cd /opt/scraper-pro

# Voir l'historique des commits
git log --oneline -10

# Exemple de sortie :
# a1b2c3d (HEAD -> main) Update: improved deduplication
# d4e5f6g Fix: dashboard crash on large jobs
# g7h8i9j Add: new validation system

# Revenir au commit précédent (remplacer par le vrai ID)
git checkout d4e5f6g

# Rebuild les images
docker-compose -f docker-compose.production.yml build

# Redémarrer
docker-compose -f docker-compose.production.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.production.yml logs -f
```

**Pour revenir à la dernière version :**

```bash
git checkout main
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

---

### Recommencer l'Installation Complète

Si tout est cassé et que vous voulez repartir de zéro :

```bash
# Étape 1 : Faire un backup de .env (contient vos secrets)
cp /opt/scraper-pro/.env ~/scraper-backup.env

# Étape 2 : Faire un backup des secrets (si vous les avez sauvegardés)
cp ~/.scraper-pro-secrets-*.txt ~/ 2>/dev/null || echo "No secrets file found"

# Étape 3 : Arrêter et supprimer tout
cd /opt/scraper-pro
docker-compose -f docker-compose.production.yml down -v
docker system prune -a --volumes -f

# Étape 4 : Supprimer le répertoire
cd ~
rm -rf /opt/scraper-pro

# Étape 5 : Réinstaller (cloner le repo)
git clone https://github.com/VOTRE_ORG/scraper-pro.git /opt/scraper-pro
cd /opt/scraper-pro

# Étape 6 : Restaurer .env
cp ~/scraper-backup.env .env
chmod 600 .env

# Étape 7 : Réinstaller avec le script automatique
bash scripts/quick_install.sh --skip-docker

# Étape 8 : Démarrer les services
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# Étape 9 : Vérifier
bash scripts/validate-installation.sh
```

✅ **Installation fraîche avec vos anciens secrets !**

---

### Sauvegarder Avant une Opération Risquée

**Bonne pratique** : Toujours sauvegarder avant de faire des changements importants.

```bash
# Script rapide de sauvegarde complète
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/scraper/emergency-backup-$BACKUP_DATE"

# Créer le répertoire de backup
mkdir -p $BACKUP_DIR

# Sauvegarder .env
cp /opt/scraper-pro/.env $BACKUP_DIR/

# Sauvegarder PostgreSQL
docker exec scraper-postgres pg_dump -U scraper_admin scraper_db | \
    gzip > $BACKUP_DIR/postgres.sql.gz

# Sauvegarder Redis (snapshot)
docker exec scraper-redis redis-cli -a $(grep REDIS_PASSWORD /opt/scraper-pro/.env | cut -d'=' -f2) \
    --rdb /data/backup.rdb 2>/dev/null || true
docker cp scraper-redis:/data/backup.rdb $BACKUP_DIR/redis.rdb

# Afficher le résultat
ls -lh $BACKUP_DIR/
du -sh $BACKUP_DIR/

echo "✅ Backup complet sauvegardé dans : $BACKUP_DIR"
```

**Pour restaurer ce backup :**

```bash
# Remplacer BACKUP_DATE par la vraie date
BACKUP_DIR="/home/scraper/emergency-backup-20260213_143000"

# Restaurer .env
cp $BACKUP_DIR/.env /opt/scraper-pro/.env

# Restaurer PostgreSQL
cd /opt/scraper-pro
docker-compose -f docker-compose.production.yml down postgres
docker volume rm scraper-pro_postgres_data
docker-compose -f docker-compose.production.yml up -d postgres
sleep 10

gunzip < $BACKUP_DIR/postgres.sql.gz | \
    docker exec -i scraper-postgres psql -U scraper_admin -d scraper_db

# Redémarrer tout
docker-compose -f docker-compose.production.yml up -d
```

---

## 🐛 12. TROUBLESHOOTING

### Problème : Container ne démarre pas

**Symptômes** : `docker ps` montre un container "Exited" ou "Restarting"

**Solution** :

```bash
# Voir les logs du container problématique
docker logs scraper-app --tail 100

# Causes courantes :
# 1. Mauvais mot de passe dans .env
# 2. Port déjà utilisé
# 3. Erreur de syntax dans .env

# Vérifier la configuration
cat .env | grep -v "^#" | grep -v "^$"

# Restart complet
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

### Problème : PostgreSQL "connection refused"

**Symptômes** : L'API ne peut pas se connecter à PostgreSQL

**Solution** :

```bash
# Vérifier que PostgreSQL tourne
docker ps | grep postgres

# Vérifier les logs
docker logs scraper-postgres --tail 50

# Tester la connexion
docker exec scraper-postgres pg_isready -U scraper_admin

# Si "accepting connections" → OK
# Si "no response" → attendre 30 secondes de plus

# Vérifier le mot de passe dans .env
grep POSTGRES_PASSWORD .env

# Recréer PostgreSQL si nécessaire
docker-compose -f docker-compose.production.yml down postgres
docker volume rm scraper-pro_postgres_data
docker-compose -f docker-compose.production.yml up -d postgres
```

### Problème : Redis "connection refused"

**Symptômes** : L'API ne peut pas se connecter à Redis

**Solution** :

```bash
# Vérifier que Redis tourne
docker ps | grep redis

# Vérifier les logs
docker logs scraper-redis --tail 50

# Tester la connexion (remplacer par le vrai mot de passe)
docker exec scraper-redis redis-cli -a YOUR_REDIS_PASSWORD ping

# Résultat attendu : PONG

# Recréer Redis si nécessaire
docker-compose -f docker-compose.production.yml down redis
docker volume rm scraper-pro_redis_data
docker-compose -f docker-compose.production.yml up -d redis
```

### Problème : Dashboard inaccessible

**Symptômes** : Erreur 502 Bad Gateway ou page blanche

**Solution** :

```bash
# Vérifier que le container tourne
docker ps | grep dashboard

# Vérifier les logs
docker logs scraper-dashboard --tail 50

# Attendre 1-2 minutes (Streamlit prend du temps à démarrer)

# Vérifier Nginx
nginx -t
systemctl status nginx

# Vérifier les logs Nginx
tail -f /var/log/nginx/error.log

# Restart le dashboard
docker restart scraper-dashboard

# Attendre 1 minute puis tester
curl -I http://localhost:8501
```

### Problème : Déduplication ne fonctionne pas

**Symptômes** : Les mêmes URLs sont scrapées plusieurs fois

**Solution** :

```bash
# Vérifier que les tables existent
docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c "\dt"

# Vous devez voir :
# - url_deduplication_cache
# - content_hash_cache

# Vérifier Redis
docker exec scraper-redis redis-cli -a YOUR_PASSWORD KEYS "dedup:*"

# Vérifier les variables d'environnement
docker exec scraper-app env | grep DEDUP

# Résultat attendu :
# DEDUP_URL_TTL_DAYS=30
# DEDUP_EMAIL_GLOBAL=true
# DEDUP_CONTENT_HASH_ENABLED=true
# DEDUP_URL_NORMALIZE=true
```

### Problème : Espace disque plein

**Symptômes** : Erreur "no space left on device"

**Solution** :

```bash
# Vérifier l'espace disque
df -h

# Voir quel répertoire utilise le plus d'espace
du -sh /var/lib/docker/*

# Nettoyer les images Docker non utilisées
docker system prune -a --volumes

# Nettoyer les backups anciens (> 30 jours)
find /home/scraper/backups -name "*.sql.gz" -mtime +30 -delete

# Nettoyer les logs
docker-compose -f docker-compose.production.yml logs --tail=0 -f
```

### Problème : SSL certificate error

**Symptômes** : Erreur "certificate expired" ou "invalid certificate"

**Solution** :

```bash
# Vérifier les certificats
certbot certificates

# Renouveler manuellement
certbot renew --force-renewal

# Redémarrer Nginx
systemctl restart nginx
```

### Problème : Job de scraping échoue

**Symptômes** : Job passe en status "failed"

**Solution** :

```bash
# Voir les logs du job
docker logs scraper-app | grep "job_id=123"

# Causes courantes :
# 1. URL invalide
# 2. Timeout (augmenter DOWNLOAD_TIMEOUT dans .env)
# 3. Site bloque le scraping (ajouter un proxy)

# Relancer le job via l'API
curl -X POST http://localhost:8000/api/v1/scraping/jobs/123/resume
```

---

## ✅ 13. CHECKLIST FINALE

Avant de mettre en production, vérifiez que tout est OK :

### Infrastructure

- [ ] Serveur Hetzner CPX31 provisionné et accessible via SSH
- [ ] Firewall configuré (ports 22, 80, 443 ouverts)
- [ ] Nom de domaine configuré avec DNS (ou accès par IP si pas de domaine)
- [ ] Docker et Docker Compose installés

### Déploiement

- [ ] Repository cloné dans `/opt/scraper-pro`
- [ ] Fichier `.env` créé avec des secrets forts (32+ caractères)
- [ ] Permissions `.env` configurées (`chmod 600`)
- [ ] 8 containers démarrés et "Up" (`docker ps`)
- [ ] API accessible et répond "ok" (`curl http://localhost:8000/health`)
- [ ] PostgreSQL accessible (`docker exec scraper-postgres pg_isready`)
- [ ] Redis accessible (`docker exec scraper-redis redis-cli ping`)

### Web Access

- [ ] Nginx installé et configuré
- [ ] Certificats SSL installés (Let's Encrypt)
- [ ] Dashboard accessible via HTTPS (`https://dashboard.example.com`)
- [ ] API accessible via HTTPS (`https://api.example.com`)
- [ ] Grafana accessible via HTTPS (`https://grafana.example.com`)
- [ ] Login Dashboard fonctionne (password depuis `.env`)

### Fonctionnalités

- [ ] Job de test lancé et terminé avec succès
- [ ] Contacts extraits visibles dans le Dashboard
- [ ] Déduplication active (stats visibles dans Dashboard)
- [ ] Grafana montre les métriques en temps réel
- [ ] Pas d'erreurs dans les logs (`docker-compose logs`)

### Maintenance

- [ ] Backup automatique configuré (cron à 2h du matin)
- [ ] Backup testé et fichier `.sql.gz` créé
- [ ] Renouvellement SSL automatique configuré (cron certbot)
- [ ] Rotation des logs Docker configurée
- [ ] Alertes email Grafana configurées (optionnel)

### Sécurité

- [ ] Tous les mots de passe sont forts (32+ caractères)
- [ ] Fichier `.env` en mode 600 (lisible seulement par vous)
- [ ] Firewall UFW activé
- [ ] PostgreSQL et Redis accessibles UNIQUEMENT depuis localhost
- [ ] Dashboard protégé par mot de passe
- [ ] API protégée par HMAC signature

---

## 🎉 FÉLICITATIONS !

**Votre système Scraper-Pro est maintenant 100% opérationnel en production !**

### Prochaines étapes recommandées

1. **Configurer MailWizz** : Ajouter vos clés API dans `.env` pour l'injection automatique
2. **Tester plusieurs jobs** : Vérifier la stabilité sur 100+ URLs
3. **Configurer les alertes email** : Être notifié en cas de problème
4. **Documenter vos listes MailWizz** : Mapper les catégories → listes dans `config/mailwizz_routing.json`
5. **Planifier la migration Google** : Quand vous serez prêt (budget proxies + SerpAPI)

### Support et Documentation

- 📖 **README.md** : Vue d'ensemble du projet
- 🏗️ **docs/ARCHITECTURE.md** : Architecture technique complète
- 🔌 **docs/API.md** : Documentation API REST
- 🔒 **docs/DEDUPLICATION_SYSTEM.md** : Système de déduplication (700+ lignes)
- 🚀 **QUICK_START.md** : Guide de démarrage rapide

### Besoin d'aide ?

- 🐛 **Issues GitHub** : Signaler un bug
- 📧 **Email** : support@sos-expat.com
- 💬 **Slack** : #scraper-pro

---

**Bon scraping !** 🚀

---

**Scraper-Pro v2.0.0 - Ultra-Professional System**
Made with ❤️ by the SOS-Expat Tech Team
