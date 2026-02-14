# 🚀 Scraper-Pro - Déploiement Rapide (5 Minutes)

**Version:** 2.0.0 | **Serveur:** Hetzner CPX31 | **Mode:** URLs Only

---

## Installation Express (Copy-Paste Ready)

### 1. Connexion Serveur

```bash
ssh root@your-server-ip

# Créer utilisateur non-root
adduser scraper
usermod -aG sudo scraper
su - scraper
```

### 2. Installation Docker (si nécessaire)

```bash
# Installation Docker + Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Logout et re-login pour appliquer les permissions
exit
```

### 3. Cloner le Projet

```bash
cd ~
git clone https://github.com/YOUR_REPO/scraper-pro.git
cd scraper-pro
```

### 4. Installation Automatique

```bash
# Lancer le script (5-10 minutes)
bash scripts/init-production.sh
```

**Le script effectue:**
- ✅ Vérification prérequis
- ✅ Génération secrets sécurisés
- ✅ Création fichier `.env`
- ✅ Configuration firewall UFW
- ✅ Pull + build images Docker
- ✅ Démarrage services
- ✅ Health checks

### 5. Sauvegarder les Secrets

```bash
# Afficher les secrets générés
cat ~/.scraper-pro-secrets-*.txt

# IMPORTANT: Copier dans gestionnaire de mots de passe
# Puis supprimer
rm ~/.scraper-pro-secrets-*.txt
```

### 6. Configurer MailWizz & Webhooks

```bash
nano .env

# Mettre à jour ces lignes:
MAILWIZZ_SOS_EXPAT_API_KEY=votre_cle_api_reelle
MAILWIZZ_ULIXAI_API_KEY=votre_cle_api_reelle
WEBHOOK_SOS_EXPAT_SECRET=secret_partage_avec_sos_expat
WEBHOOK_ULIXAI_SECRET=secret_partage_avec_ulixai

# Sauvegarder: Ctrl+O, Enter, Ctrl+X
```

### 7. Redémarrer les Services

```bash
docker-compose -f docker-compose.production.yml restart
```

### 8. Vérifier le Statut

```bash
# Statut containers
docker ps

# Health checks
curl http://localhost:8000/health
curl http://localhost:8501
curl http://localhost:3000/api/health

# Logs
docker-compose -f docker-compose.production.yml logs -f
```

---

## Accès Services (Localhost)

| Service | URL | Credentials |
|---------|-----|-------------|
| **Dashboard** | `http://localhost:8501` | Password dans secrets file |
| **Grafana** | `http://localhost:3000` | admin / password dans secrets file |
| **Prometheus** | `http://localhost:9090` | Pas de login |
| **API** | `http://localhost:8000` | HMAC auth |

---

## Configuration Nginx + SSL (Optionnel mais Recommandé)

### 1. Installer Nginx

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

### 2. Créer Configuration

```bash
sudo nano /etc/nginx/sites-available/scraper-pro
```

```nginx
# Dashboard
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
    }
}
```

### 3. Activer & Tester

```bash
sudo ln -s /etc/nginx/sites-available/scraper-pro /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Obtenir SSL (Let's Encrypt)

```bash
sudo certbot --nginx -d dashboard.your-domain.com -d monitoring.your-domain.com
```

**Renouvellement automatique:** Certbot configure un cron job automatiquement ✅

---

## Commandes Utiles

```bash
# ─── Containers ──────────────────────────────
docker ps                                         # Statut
docker-compose -f docker-compose.production.yml logs -f  # Logs
docker-compose -f docker-compose.production.yml restart  # Restart
docker stats                                      # CPU/RAM

# ─── PostgreSQL ──────────────────────────────
docker exec -it scraper-postgres psql -U scraper_admin -d scraper_db
docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c "SELECT pg_size_pretty(pg_database_size('scraper_db'));"

# ─── Redis ───────────────────────────────────
docker exec -it scraper-redis redis-cli -a "$REDIS_PASSWORD"
docker exec scraper-redis redis-cli -a "$REDIS_PASSWORD" DBSIZE

# ─── Backup ──────────────────────────────────
bash scripts/backup-postgres.sh

# ─── Firewall ────────────────────────────────
sudo ufw status verbose
```

---

## Performance Attendue

| Métrique | Valeur |
|----------|--------|
| **URLs/minute** | 50-100 |
| **URLs/heure** | 3,000-6,000 |
| **URLs/jour** | 70,000-150,000 |
| **Emails/jour** | 10,000-30,000 |
| **CPU moyen** | 40-60% |
| **RAM moyenne** | 6-7GB / 8GB |

---

## Monitoring

### Dashboard Grafana

1. Accéder: `https://monitoring.your-domain.com` (ou `http://localhost:3000`)
2. Login: `admin` / password du secrets file
3. Dashboard déjà importé: **Scraper-Pro Production**

### Métriques Clés

- URLs scrapées (total + taux)
- Emails extraits (total + taux)
- CPU/RAM usage
- PostgreSQL/Redis stats
- Deduplication stats
- HTTP response codes
- Request latency (p95, p99)

---

## Troubleshooting

### API ne démarre pas

```bash
docker logs scraper-app -f
docker-compose -f docker-compose.production.yml restart scraper
```

### PostgreSQL erreur de connexion

```bash
docker exec scraper-postgres pg_isready -U scraper_admin
docker-compose -f docker-compose.production.yml restart postgres
```

### Redis nécessite un mot de passe

```bash
# Vérifier la variable
echo $REDIS_PASSWORD

# Tester
docker exec scraper-redis redis-cli -a "$REDIS_PASSWORD" PING
```

### Dashboard Streamlit ne charge pas

```bash
docker logs scraper-dashboard -f
docker-compose -f docker-compose.production.yml restart dashboard
```

---

## Backup Automatique

```bash
# Configurer backup quotidien (2h du matin)
crontab -e

# Ajouter cette ligne:
0 2 * * * /home/scraper/scraper-pro/scripts/backup-postgres.sh
```

---

## Sécurité Checklist

- [x] Firewall UFW activé (ports 22, 80, 443)
- [x] Services bindés sur 127.0.0.1 uniquement
- [x] Nginx reverse proxy avec SSL
- [x] Secrets forts (32-64 chars)
- [x] Permissions `.env` = 600
- [x] Fail2ban pour SSH (optionnel)

---

## Documentation Complète

- **Guide complet:** `PRODUCTION_DEPLOYMENT_GUIDE.md` (25KB, 1100+ lignes)
- **Récapitulatif:** `PRODUCTION_FILES_SUMMARY.md`
- **Architecture:** `ULTRA_PRO_SYSTEM_READY.md`
- **Deduplication:** `docs/DEDUPLICATION_SYSTEM.md`
- **FAQ:** `FAQ_CRITIQUE.md`

---

## Support

En cas de problème:

1. Consulter `FAQ_CRITIQUE.md`
2. Vérifier les logs: `docker-compose logs -f`
3. Consulter Grafana: `https://monitoring.your-domain.com`
4. Vérifier PostgreSQL/Redis health

---

## Coûts Mensuels

| Composant | Coût |
|-----------|------|
| Hetzner CPX31 | €10.49 (~$11.50) |
| Domaine + SSL | ~$1/mois |
| **Total** | **~$15/mois** |

**Économie vs mode Full (avec proxies):** $485-1985/mois 💰

---

## One-Liner (pour les pros)

```bash
ssh scraper@your-server && cd ~ && git clone https://github.com/YOUR_REPO/scraper-pro.git && cd scraper-pro && bash scripts/init-production.sh && echo "✅ Installation terminée!"
```

---

**Version:** 2.0.0
**Date:** 2026-02-13
**Status:** Production-Ready ✅

**Bon déploiement! 🚀**
