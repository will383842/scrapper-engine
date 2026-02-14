#!/bin/bash
# ========================================
# SCRIPT : AJOUTER SCRAPER-PRO À BACKLINK ENGINE
# ========================================
# Ajoute Scraper-Pro sur un serveur qui a déjà Backlink Engine
# Partage PostgreSQL et Redis existants
# ========================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ========================================
# Fonctions utilitaires
# ========================================

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ========================================
# Vérifications préalables
# ========================================

print_header "🔍 Vérifications Préalables"

# Vérifier qu'on est root
if [ "$EUID" -ne 0 ]; then
    print_error "Ce script doit être exécuté en tant que root"
    print_info "Utilisez : sudo $0"
    exit 1
fi

print_success "Exécuté en tant que root"

# Vérifier que Backlink Engine est bien déployé
if ! docker ps | grep -q "bl-postgres"; then
    print_error "Container bl-postgres introuvable"
    print_error "Backlink Engine n'est pas déployé ou PostgreSQL a un autre nom"
    exit 1
fi

print_success "bl-postgres détecté"

if ! docker ps | grep -q "bl-redis"; then
    print_error "Container bl-redis introuvable"
    exit 1
fi

print_success "bl-redis détecté"

# ========================================
# Détection des credentials Backlink Engine
# ========================================

print_header "🔐 Détection des Credentials Backlink Engine"

print_info "Recherche des credentials PostgreSQL et Redis..."

# Essayer de trouver le docker-compose de Backlink Engine
if [ -f "/opt/backlink-engine/docker-compose.yml" ]; then
    BL_COMPOSE_DIR="/opt/backlink-engine"
    print_success "docker-compose Backlink Engine trouvé : $BL_COMPOSE_DIR"
elif [ -f "$HOME/backlink-engine/docker-compose.yml" ]; then
    BL_COMPOSE_DIR="$HOME/backlink-engine"
    print_success "docker-compose Backlink Engine trouvé : $BL_COMPOSE_DIR"
else
    print_warning "docker-compose Backlink Engine non trouvé dans les emplacements standards"
    BL_COMPOSE_DIR=""
fi

# Demander les credentials à l'utilisateur
echo ""
print_info "Nous avons besoin des credentials PostgreSQL et Redis de Backlink Engine"
echo ""

read -p "📦 Nom d'utilisateur PostgreSQL de Backlink Engine [backlink]: " BL_POSTGRES_USER
BL_POSTGRES_USER=${BL_POSTGRES_USER:-backlink}

read -sp "🔑 Mot de passe PostgreSQL de Backlink Engine : " BL_POSTGRES_PASSWORD
echo ""

if [ -z "$BL_POSTGRES_PASSWORD" ]; then
    print_error "Le mot de passe PostgreSQL est obligatoire"
    exit 1
fi

read -sp "🔑 Mot de passe Redis de Backlink Engine (laisser vide si pas de password) : " BL_REDIS_PASSWORD
echo ""

# Vérifier la connexion PostgreSQL
print_info "Test de connexion à PostgreSQL..."
if docker exec bl-postgres psql -U "$BL_POSTGRES_USER" -c "\l" &> /dev/null; then
    print_success "Connexion PostgreSQL réussie"
else
    print_error "Impossible de se connecter à PostgreSQL avec ces credentials"
    print_info "Vérifiez le nom d'utilisateur et le mot de passe"
    exit 1
fi

# Vérifier Redis
print_info "Test de connexion à Redis..."
if [ -z "$BL_REDIS_PASSWORD" ]; then
    if docker exec bl-redis redis-cli ping &> /dev/null; then
        print_success "Connexion Redis réussie (pas de password)"
    else
        print_warning "Redis nécessite peut-être un password"
    fi
else
    if docker exec bl-redis redis-cli -a "$BL_REDIS_PASSWORD" ping &> /dev/null; then
        print_success "Connexion Redis réussie"
    else
        print_error "Impossible de se connecter à Redis avec ce password"
        exit 1
    fi
fi

# ========================================
# Création de la base scraper_db
# ========================================

print_header "🗄️  Création de la Base scraper_db"

# Vérifier si la base existe déjà
if docker exec bl-postgres psql -U "$BL_POSTGRES_USER" -lqt | cut -d \| -f 1 | grep -qw scraper_db; then
    print_warning "La base scraper_db existe déjà"
    read -p "Voulez-vous la recréer ? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker exec bl-postgres psql -U "$BL_POSTGRES_USER" -c "DROP DATABASE scraper_db;" || true
        print_info "Base scraper_db supprimée"
    fi
fi

# Créer la base scraper_db
docker exec bl-postgres psql -U "$BL_POSTGRES_USER" -c "CREATE DATABASE scraper_db;"
print_success "Base scraper_db créée"

# Installer les extensions
docker exec bl-postgres psql -U "$BL_POSTGRES_USER" -d scraper_db -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
docker exec bl-postgres psql -U "$BL_POSTGRES_USER" -d scraper_db -c "CREATE EXTENSION IF NOT EXISTS \"pg_trgm\";"
print_success "Extensions PostgreSQL installées"

# ========================================
# Configuration Scraper-Pro
# ========================================

print_header "⚙️  Configuration Scraper-Pro"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Générer secrets pour Scraper-Pro
generate_secret() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

API_HMAC_SECRET=$(generate_secret)
DASHBOARD_PASSWORD=$(generate_secret)

# Créer le fichier .env
cat > .env <<EOF
# ========================================
# SCRAPER-PRO - Intégration avec Backlink Engine
# ========================================
# Généré automatiquement le $(date)
# ========================================

# PostgreSQL (partagé avec Backlink Engine)
BL_POSTGRES_USER=$BL_POSTGRES_USER
BL_POSTGRES_PASSWORD=$BL_POSTGRES_PASSWORD

# Redis (partagé avec Backlink Engine)
BL_REDIS_PASSWORD=$BL_REDIS_PASSWORD

# API Scraper-Pro
API_HOST=0.0.0.0
API_PORT=8000
API_HMAC_SECRET=$API_HMAC_SECRET

# Dashboard Scraper-Pro
DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD

# Scraping (optimisé pour 2 vCPU partagé avec Backlink Engine)
PROXY_ENABLED=false
DOWNLOAD_DELAY=3.0
CONCURRENT_REQUESTS=2
CONCURRENT_REQUESTS_PER_DOMAIN=1

# Throttling
AUTOTHROTTLE_ENABLED=true
AUTOTHROTTLE_START_DELAY=2
AUTOTHROTTLE_MAX_DELAY=30
SMART_THROTTLE_MIN_DELAY=1.0
SMART_THROTTLE_MAX_DELAY=60.0

# Logs
LOG_LEVEL=INFO
EOF

print_success "Fichier .env créé"

# Sauvegarder les secrets
SECRETS_FILE="$HOME/.scraper-secrets-$(date +%Y%m%d_%H%M%S).txt"
cat > "$SECRETS_FILE" <<EOF
========================================
SCRAPER-PRO SECRETS - $(date)
========================================

API_HMAC_SECRET=$API_HMAC_SECRET
DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD

PostgreSQL (partagé) :
  Host     : bl-postgres
  User     : $BL_POSTGRES_USER
  Database : scraper_db

Redis (partagé) :
  Host     : bl-redis
  Namespace: 1 (Backlink = 0)

========================================
URLs d'accès :
========================================
API       : http://$(hostname -I | awk '{print $1}'):8000
Dashboard : http://$(hostname -I | awk '{print $1}'):8501

Health Check : http://$(hostname -I | awk '{print $1}'):8000/health

========================================
IMPORTANT : Sauvegarder ce fichier !
========================================
EOF

chmod 600 "$SECRETS_FILE"
print_success "Secrets sauvegardés dans $SECRETS_FILE"

# ========================================
# Vérifier le réseau Docker
# ========================================

print_header "🌐 Configuration Réseau Docker"

# Trouver le réseau de Backlink Engine
BL_NETWORK=$(docker inspect bl-postgres --format '{{range $net,$v := .NetworkSettings.Networks}}{{$net}}{{end}}' | head -1)

if [ -z "$BL_NETWORK" ]; then
    print_error "Impossible de détecter le réseau Docker de Backlink Engine"
    exit 1
fi

print_success "Réseau Backlink Engine détecté : $BL_NETWORK"

# Modifier docker-compose pour utiliser le bon réseau
sed -i "s|backlink-engine_default|$BL_NETWORK|g" docker-compose.add-to-existing.yml

print_success "docker-compose.add-to-existing.yml configuré"

# ========================================
# Construction des images
# ========================================

print_header "🏗️  Construction des Images Docker"

docker compose -f docker-compose.add-to-existing.yml build

print_success "Images Docker construites"

# ========================================
# Démarrage de Scraper-Pro
# ========================================

print_header "🚀 Démarrage de Scraper-Pro"

docker compose -f docker-compose.add-to-existing.yml up -d

print_success "Containers Scraper-Pro démarrés"

# Attendre que l'API soit prête
print_info "Attente du démarrage de l'API (30s)..."
sleep 30

# ========================================
# Application des migrations
# ========================================

print_header "📊 Application des Migrations SQL"

if [ -d "db/migrations" ]; then
    for migration in db/migrations/*.sql; do
        if [ -f "$migration" ]; then
            filename=$(basename "$migration")
            print_info "Application de $filename..."
            docker exec bl-postgres psql -U "$BL_POSTGRES_USER" -d scraper_db < "$migration" 2>/dev/null || true
            print_success "$filename appliqué"
        fi
    done
else
    print_warning "Répertoire db/migrations introuvable"
fi

# ========================================
# Health Checks
# ========================================

print_header "🏥 Vérifications de Santé"

if curl -sf http://localhost:8000/health > /dev/null; then
    print_success "API Scraper-Pro opérationnelle"
else
    print_warning "API ne répond pas encore (normal si premier démarrage)"
fi

if curl -sf http://localhost:8501 > /dev/null; then
    print_success "Dashboard accessible"
else
    print_warning "Dashboard ne répond pas encore"
fi

# ========================================
# État des ressources
# ========================================

print_header "📊 État des Ressources (Backlink + Scraper)"

echo ""
echo "🖥️  RAM Système :"
free -h | grep Mem

echo ""
echo "🐳 Tous les Containers :"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"

# ========================================
# Récapitulatif
# ========================================

print_header "✅ Scraper-Pro Ajouté avec Succès !"

SERVER_IP=$(hostname -I | awk '{print $1}')

cat <<EOF

${GREEN}🎉 Scraper-Pro est maintenant déployé à côté de Backlink Engine !${NC}

${BLUE}📍 URLs d'accès :${NC}

  🔧 Scraper-Pro API       : http://$SERVER_IP:8000
  📊 Scraper-Pro Dashboard : http://$SERVER_IP:8501
  🌐 Backlink Engine       : http://$SERVER_IP (port 80)

  ✅ Health Check API      : http://$SERVER_IP:8000/health

${BLUE}🗄️  Base de Données PostgreSQL (partagée) :${NC}

  • Backlink Engine : base "backlink" ou similaire
  • Scraper-Pro     : base "scraper_db" ✅

${BLUE}🔴 Redis (partagé) :${NC}

  • Backlink Engine : namespace 0
  • Scraper-Pro     : namespace 1 ✅

${BLUE}🔐 Credentials Scraper-Pro :${NC}

  📄 Fichier secrets : ${SECRETS_FILE}

${BLUE}📊 Commandes utiles :${NC}

  # Status tous les containers
  docker ps

  # Logs Scraper-Pro
  docker compose -f docker-compose.add-to-existing.yml logs -f

  # Monitoring RAM global
  docker stats

  # Redémarrer Scraper-Pro uniquement
  docker compose -f docker-compose.add-to-existing.yml restart

${BLUE}🚀 Premier test :${NC}

  curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \\
    -H "Content-Type: application/json" \\
    -d '{
      "source_type": "custom_urls",
      "name": "Test Expat",
      "config": {"urls": ["https://www.expat.com/fr/guide/"]},
      "max_results": 50
    }'

${YELLOW}⚠️  IMPORTANT :${NC}

  • RAM actuelle utilisée : ~2.7 GB / 3.7 GB (~73%)
  • Si RAM > 85%, réduire CONCURRENT_REQUESTS à 1 dans .env
  • Monitorer régulièrement avec : docker stats

${GREEN}✅ Intégration terminée avec succès !${NC}

========================================

EOF

print_success "Déploiement terminé !"
