# Scripts de Déploiement - Scraper-Pro

Ce répertoire contient tous les scripts nécessaires pour installer, configurer et maintenir Scraper-Pro en production.

## 📋 Vue d'Ensemble des Scripts

| Script | Description | Durée | Quand l'utiliser |
|--------|-------------|-------|------------------|
| `quick_install.sh` | Installation automatique complète | 10-15 min | Première installation |
| `validate-installation.sh` | Validation de l'installation | 1 min | Après installation ou mise à jour |
| `setup-nginx.sh` | Configuration Nginx + SSL | 5-10 min | Après quick_install.sh |
| **`monitor_job.sh`** | **Surveillance temps réel d'un job** | Continu | Pendant un scraping |
| **`monitor_job.py`** | **Surveillance temps réel (Python)** | Continu | Pendant un scraping |

---

## 📊 monitor_job.sh / monitor_job.py

**Surveillance en temps réel des jobs de scraping**

### Fonctionnalités

- ✅ Affichage du status en temps réel
- ✅ Barre de progression visuelle
- ✅ Compteurs (pages, contacts, erreurs)
- ✅ Détection automatique de fin
- ✅ Lien vers logs en cas d'erreur
- ✅ Support multi-plateforme

### Usage

**Version Bash (Linux/Mac/WSL) :**
```bash
# Surveiller un job (rafraîchir toutes les 10s)
./scripts/monitor_job.sh 123

# Intervalle personnalisé (5 secondes)
./scripts/monitor_job.sh 123 5

# API distante
API_URL=http://prod-server:8000 ./scripts/monitor_job.sh 123
```

**Version Python (Multi-plateforme) :**
```bash
# Installer les dépendances (optionnelles pour affichage enrichi)
pip install requests rich

# Surveiller un job
python scripts/monitor_job.py 123

# Intervalle personnalisé
python scripts/monitor_job.py 123 --interval 5

# API distante
python scripts/monitor_job.py 123 --api-url http://prod-server:8000
```

### Exemple de sortie (Bash avec jq)

```
[2026-02-13 14:30:45] Rafraîchissement #12
  Status      : ⚙️  RUNNING
  Progress    : [████████████░░░░░░░░] 60.5%
  Type        : google_search
  Pages       : 61
  Contacts    : 23
  Errors      : 0

🏁 Job terminé avec status: completed

📊 Résumé final:
  • Pages scrapées    : 100
  • Contacts extraits : 42
  • Erreurs           : 2
```

### Quand l'utiliser

- ✅ Pendant un long scraping (suivre la progression)
- ✅ Debugging (détecter rapidement les erreurs)
- ✅ Démonstration client (montrer l'avancement)
- ✅ Tests de performance

### Workflow avec monitoring

```bash
# 1. Créer un job
JOB_ID=$(curl -s -X POST http://localhost:8000/api/v1/scraping/jobs/simple \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "custom_urls",
    "name": "Test",
    "config": {"urls": ["https://example.com"]}
  }' | jq -r '.job_id')

# 2. Surveiller en temps réel
./scripts/monitor_job.sh $JOB_ID

# OU en arrière-plan avec logs
nohup python scripts/monitor_job.py $JOB_ID > job_$JOB_ID.log 2>&1 &
```

---

## 🚀 quick_install.sh

**Installation automatique complète de Scraper-Pro**

### Fonctionnalités

- ✅ Met à jour le système Ubuntu/Debian
- ✅ Installe Docker + Docker Compose
- ✅ Configure le firewall UFW
- ✅ Clone le repository (si besoin)
- ✅ **Auto-génère des secrets forts** (PostgreSQL, Redis, API, Dashboard, Grafana)
- ✅ **Sauvegarde les secrets** dans `~/.scraper-pro-secrets-YYYYMMDD_HHMMSS.txt`
- ✅ Build les images Docker
- ✅ Démarre tous les services
- ✅ Vérifie la santé de l'API

### Usage

```bash
# Installation complète (recommandé)
bash scripts/quick_install.sh

# Skiper l'installation Docker (si déjà installé)
bash scripts/quick_install.sh --skip-docker

# Nettoyage complet (DESTRUCTIF - supprime toutes les données)
bash scripts/quick_install.sh --cleanup
```

### Ce qui est auto-généré

Le script génère automatiquement :

- **POSTGRES_PASSWORD** : 32 caractères alphanumériques
- **REDIS_PASSWORD** : 32 caractères alphanumériques
- **API_HMAC_SECRET** : 64 caractères hexadécimaux
- **DASHBOARD_PASSWORD** : 16 caractères alphanumériques
- **GRAFANA_PASSWORD** : 16 caractères alphanumériques

Tous ces secrets sont sauvegardés dans :
- `~/.scraper-pro-secrets-YYYYMMDD_HHMMSS.txt` (fichier sécurisé avec permissions 600)
- `/opt/scraper-pro/.env` (fichier de configuration)

### Après l'installation

1. **Sauvegarder vos secrets** :
   ```bash
   # Copier le fichier vers un endroit sûr (password manager, etc.)
   cat ~/.scraper-pro-secrets-*.txt

   # Puis supprimer du serveur
   rm ~/.scraper-pro-secrets-*.txt
   ```

2. **Configurer les secrets optionnels** (MailWizz, Webhooks) :
   ```bash
   nano /opt/scraper-pro/.env
   # Modifier MAILWIZZ_*_API_KEY et WEBHOOK_*_SECRET
   ```

3. **Redémarrer les services** :
   ```bash
   cd /opt/scraper-pro
   docker-compose -f docker-compose.production.yml restart
   ```

4. **Valider l'installation** :
   ```bash
   bash scripts/validate-installation.sh
   ```

---

## ✅ validate-installation.sh

**Validation automatique de tous les composants**

### Fonctionnalités

- ✅ Vérifie que Docker fonctionne
- ✅ Vérifie que tous les containers sont "Up"
- ✅ Teste les health checks (API, PostgreSQL, Redis)
- ✅ Vérifie l'accessibilité (Dashboard, Grafana, Prometheus)
- ✅ Vérifie le schéma de la base de données
- ✅ Teste la connectivité réseau inter-containers
- ✅ Vérifie l'espace disque et la mémoire
- ✅ Vérifie les permissions du fichier `.env`
- ✅ Détecte les mots de passe par défaut (CHANGE_ME)

### Usage

```bash
# Validation standard
bash scripts/validate-installation.sh

# Validation avec sortie détaillée (verbose)
bash scripts/validate-installation.sh --verbose
bash scripts/validate-installation.sh -v
```

### Sortie

**Si tout est OK** :
```
=========================================
  Scraper-Pro Installation Validator
=========================================

=== Docker Daemon ===
Checking Docker Daemon Running... ✅ PASS

=== Docker Containers ===
Checking PostgreSQL Container... ✅ PASS
Checking Redis Container... ✅ PASS
Checking API Container... ✅ PASS
...

=========================================
  Validation Summary
=========================================
Total Checks: 20
Passed: 20

✅ All checks passed! Installation is healthy.
```

**Si des problèmes sont détectés** :
```
Checking Redis Ping... ❌ FAIL

=========================================
  Validation Summary
=========================================
Total Checks: 20
Passed: 18
Failed: 2

⚠️ Some checks failed. Review the output above.

Troubleshooting tips:
  1. Check Docker logs:
     docker-compose -f docker-compose.production.yml logs
  ...
```

### Quand l'utiliser

- ✅ Après l'installation initiale
- ✅ Après une mise à jour du code
- ✅ Après un redémarrage du serveur
- ✅ Pour diagnostiquer un problème
- ✅ Dans un script de monitoring (cron)

### Automatisation (Monitoring)

Vous pouvez automatiser ce script pour surveiller votre installation :

```bash
# Ajouter un cron job (toutes les heures)
crontab -e

# Ajouter cette ligne :
0 * * * * /opt/scraper-pro/scripts/validate-installation.sh >> /var/log/scraper-health.log 2>&1
```

---

## 🌐 setup-nginx.sh

**Configuration automatique de Nginx + SSL (Let's Encrypt)**

### Fonctionnalités

- ✅ Installe Nginx et Certbot
- ✅ Vérifie la configuration DNS
- ✅ Crée 3 configurations Nginx :
  - **dashboard.$DOMAIN** → Streamlit (port 8501)
  - **api.$DOMAIN** → FastAPI (port 8000)
  - **grafana.$DOMAIN** → Grafana (port 3000)
- ✅ Active WebSocket pour Streamlit et Grafana
- ✅ Installe les certificats SSL Let's Encrypt
- ✅ Configure le renouvellement automatique SSL
- ✅ Configure le firewall UFW

### Usage

```bash
# Avec votre domaine (email auto-généré)
bash scripts/setup-nginx.sh yourdomain.com

# Avec email personnalisé
bash scripts/setup-nginx.sh yourdomain.com admin@yourdomain.com
```

### Prérequis DNS

**AVANT** de lancer le script, configurez 3 enregistrements DNS de type A :

| Nom | Type | Valeur |
|-----|------|--------|
| dashboard.yourdomain.com | A | Votre IP serveur |
| api.yourdomain.com | A | Votre IP serveur |
| grafana.yourdomain.com | A | Votre IP serveur |

**Vérifier la propagation DNS** :
```bash
# Depuis votre ordinateur local
dig dashboard.yourdomain.com +short
dig api.yourdomain.com +short
dig grafana.yourdomain.com +short

# Résultat attendu : votre IP serveur
```

### Exemple de sortie

```
=========================================
  Nginx + SSL Setup for Scraper-Pro
=========================================

Domain: example.com
Email: admin@example.com
Subdomains:
  - dashboard.example.com
  - api.example.com
  - grafana.example.com

[INFO] Step 1/7: Installing Nginx and Certbot...
[SUCCESS] Nginx installed
[SUCCESS] Certbot installed

[INFO] Step 2/7: Checking DNS configuration...
...

=========================================
  ✅ Setup Complete!
=========================================

Access your services:

  📊 Dashboard (Streamlit):
     https://dashboard.example.com

  🔌 API (FastAPI):
     https://api.example.com
     https://api.example.com/docs

  📈 Grafana (Monitoring):
     https://grafana.example.com
```

### Certificats SSL

- ✅ Certificats Let's Encrypt (gratuits, reconnus par tous les navigateurs)
- ✅ Renouvellement automatique tous les 60 jours (cron job)
- ✅ HTTP → HTTPS redirect automatique
- ✅ Note de sécurité A+ (SSL Labs)

### Commandes de maintenance

```bash
# Vérifier le statut des certificats
sudo certbot certificates

# Renouveler manuellement
sudo certbot renew

# Tester le renouvellement
sudo certbot renew --dry-run

# Tester la configuration Nginx
sudo nginx -t

# Recharger Nginx
sudo systemctl reload nginx

# Voir les logs Nginx
sudo tail -f /var/log/nginx/scraper-*-error.log
```

---

## 🔧 Workflow Recommandé

### Installation Initiale (Serveur Vierge)

```bash
# 1. Se connecter au serveur
ssh root@VOTRE_IP

# 2. Cloner le repository
git clone https://github.com/VOTRE_ORG/scraper-pro.git /opt/scraper-pro
cd /opt/scraper-pro

# 3. Lancer l'installation automatique
bash scripts/quick_install.sh

# 4. Sauvegarder les secrets générés
cat ~/.scraper-pro-secrets-*.txt
# Copier dans un password manager, puis :
rm ~/.scraper-pro-secrets-*.txt

# 5. Valider l'installation
bash scripts/validate-installation.sh

# 6. Configurer Nginx + SSL (si vous avez un domaine)
bash scripts/setup-nginx.sh yourdomain.com admin@yourdomain.com

# 7. Tester l'accès
# Ouvrir https://dashboard.yourdomain.com dans votre navigateur
```

### Mise à Jour du Code

```bash
# 1. Se connecter
ssh root@VOTRE_IP
cd /opt/scraper-pro

# 2. Sauvegarder .env
cp .env .env.backup

# 3. Pull les changements
git pull origin main

# 4. Rebuild et redémarrer
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# 5. Valider
bash scripts/validate-installation.sh
```

### Diagnostic de Problème

```bash
# 1. Valider l'installation
bash scripts/validate-installation.sh --verbose

# 2. Voir les logs
docker-compose -f docker-compose.production.yml logs -f

# 3. Vérifier un service spécifique
docker logs scraper-app --tail 100
docker logs scraper-postgres --tail 100

# 4. Redémarrer un service
docker restart scraper-app
```

---

## 📚 Documentation Complète

Pour plus d'informations, consultez :

- **DEPLOYMENT_PRODUCTION.md** : Guide de déploiement complet (étape par étape)
- **QUICK_START.md** : Guide de démarrage rapide
- **docs/ARCHITECTURE.md** : Architecture technique
- **docs/API.md** : Documentation de l'API REST
- **docs/DEDUPLICATION_SYSTEM.md** : Système de déduplication

---

## 🛡️ Sécurité

### Bonnes pratiques

1. ✅ **Sauvegarder les secrets** dans un password manager (1Password, LastPass, Bitwarden)
2. ✅ **Supprimer les fichiers de secrets** du serveur après sauvegarde
3. ✅ **Permissions strictes** sur `.env` (chmod 600)
4. ✅ **Firewall activé** (UFW)
5. ✅ **SSL/TLS** sur tous les endpoints
6. ✅ **Backups automatiques** de PostgreSQL (cron)
7. ✅ **Monitoring actif** avec Grafana + Prometheus

### Checklist de sécurité

```bash
# Vérifier les permissions .env
ls -la /opt/scraper-pro/.env
# Attendu : -rw------- (600)

# Vérifier le firewall
sudo ufw status
# Attendu : 22, 80, 443 autorisés

# Vérifier les certificats SSL
sudo certbot certificates
# Attendu : Expiry date dans 60-90 jours

# Vérifier les mots de passe par défaut
grep "CHANGE_ME" /opt/scraper-pro/.env
# Attendu : aucune correspondance

# Vérifier les backups
ls -lh /home/scraper/backups/
# Attendu : backups récents (< 24h)
```

---

## 🆘 Support

En cas de problème :

1. Consulter **DEPLOYMENT_PRODUCTION.md** section "Troubleshooting"
2. Vérifier les logs : `docker-compose logs -f`
3. Valider l'installation : `bash scripts/validate-installation.sh --verbose`
4. Ouvrir une issue sur GitHub

---

**Scraper-Pro v2.0.0 - Scripts de Déploiement**
Made with ❤️ by the SOS-Expat Tech Team
