#!/bin/bash
# ========================================
# SCRIPT DE DÉPLOIEMENT SCRAPER-PRO SEUL
# ========================================
# Déploiement de Scraper-Pro sur serveur 2 vCPU / 4 GB RAM
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

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    print_warning "Docker n'est pas installé. Installation en cours..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    print_success "Docker installé"
else
    print_success "Docker est installé"
fi

# Vérifier Docker Compose
if ! docker compose version &> /dev/null; then
    print_warning "Docker Compose plugin manquant. Installation en cours..."
    apt-get update
    apt-get install -y docker-compose-plugin
    print_success "Docker Compose installé"
else
    print_success "Docker Compose est installé"
fi

# ========================================
# Ressources système
# ========================================

print_header "📊 Ressources Système"

TOTAL_RAM=$(free -m | grep Mem | awk '{print $2}')
TOTAL_CPU=$(nproc)
TOTAL_DISK=$(df -h / | tail -1 | awk '{print $4}')

echo "CPU   : $TOTAL_CPU vCPU"
echo "RAM   : $TOTAL_RAM MB"
echo "Disk  : $TOTAL_DISK disponible"

if [ "$TOTAL_RAM" -lt 3500 ]; then
    print_warning "RAM < 4 GB détectée"
fi

print_success "Ressources système vérifiées"

# ========================================
# Configuration du projet
# ========================================

print_header "⚙️  Configuration du Projet"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

print_info "Répertoire du projet : $PROJECT_DIR"

# Vérifier que docker-compose.scraper-only.yml existe
if [ ! -f "docker-compose.scraper-only.yml" ]; then
    print_error "docker-compose.scraper-only.yml introuvable"
    exit 1
fi

print_success "Fichier docker-compose.scraper-only.yml trouvé"

# ========================================
# Génération des secrets
# ========================================

print_header "🔐 Configuration des Secrets"

if [ ! -f ".env" ]; then
    print_info "Création du fichier .env"
    touch .env
fi

# Fonction pour générer un secret
generate_secret() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Vérifier si les secrets existent déjà
if ! grep -q "POSTGRES_PASSWORD=" .env || grep -q "POSTGRES_PASSWORD=$" .env; then
    print_info "Génération de nouveaux secrets..."

    POSTGRES_USER="scraper_user"
    POSTGRES_PASSWORD=$(generate_secret)
    REDIS_PASSWORD=$(generate_secret)
    API_HMAC_SECRET=$(generate_secret)
    DASHBOARD_PASSWORD=$(generate_secret)

    cat > .env <<EOF
# ========================================
# SCRAPER-PRO - Configuration
# ========================================
# Généré automatiquement le $(date)
# ========================================

# PostgreSQL
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis
REDIS_PASSWORD=$REDIS_PASSWORD

# API
API_HOST=0.0.0.0
API_PORT=8000
API_HMAC_SECRET=$API_HMAC_SECRET

# Dashboard
DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD

# Scraping (optimisé pour 2 vCPU)
PROXY_ENABLED=false
DOWNLOAD_DELAY=2.5
CONCURRENT_REQUESTS=3
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

    print_success "Secrets générés et sauvegardés dans .env"

    # Sauvegarder les secrets dans un fichier sécurisé
    SECRETS_FILE="$HOME/.scraper-secrets-$(date +%Y%m%d_%H%M%S).txt"
    cat > "$SECRETS_FILE" <<EOF
========================================
SCRAPER-PRO SECRETS - $(date)
========================================

POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
API_HMAC_SECRET=$API_HMAC_SECRET
DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD

========================================
URLs d'accès :
========================================
API       : http://$(hostname -I | awk '{print $1}'):8000
Dashboard : http://$(hostname -I | awk '{print $1}'):8501

Health Check : http://$(hostname -I | awk '{print $1}'):8000/health

========================================
IMPORTANT : Sauvegarder ce fichier !
Fichier : $SECRETS_FILE
========================================
EOF

    chmod 600 "$SECRETS_FILE"
    print_success "Secrets sauvegardés dans $SECRETS_FILE"
else
    print_info "Secrets déjà configurés dans .env"
fi

# ========================================
# Arrêt des services existants
# ========================================

print_header "🛑 Arrêt des Services Existants"

if docker compose -f docker-compose.scraper-only.yml ps --quiet 2>/dev/null | grep -q .; then
    print_info "Services existants détectés. Arrêt en cours..."
    docker compose -f docker-compose.scraper-only.yml down
    print_success "Services arrêtés"
else
    print_info "Aucun service Scraper-Pro existant"
fi

# ========================================
# Construction des images
# ========================================

print_header "🏗️  Construction des Images Docker"

docker compose -f docker-compose.scraper-only.yml build

print_success "Images Docker construites"

# ========================================
# Démarrage des services
# ========================================

print_header "🚀 Démarrage des Services"

docker compose -f docker-compose.scraper-only.yml up -d

# Attendre PostgreSQL
print_info "Attente du démarrage de PostgreSQL..."
sleep 10

MAX_RETRIES=30
RETRY_COUNT=0

while ! docker exec scraper-postgres pg_isready -U scraper_user &> /dev/null; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -gt $MAX_RETRIES ]; then
        print_error "PostgreSQL n'a pas démarré"
        exit 1
    fi
    echo -n "."
    sleep 2
done

echo ""
print_success "PostgreSQL est prêt"

# Vérifier Redis
if docker exec scraper-redis redis-cli ping &> /dev/null; then
    print_success "Redis est prêt"
fi

# ========================================
# Application des migrations
# ========================================

print_header "📊 Application des Migrations SQL"

if [ -d "db/migrations" ]; then
    for migration in db/migrations/*.sql; do
        if [ -f "$migration" ]; then
            filename=$(basename "$migration")
            print_info "Application de $filename..."
            docker exec -i scraper-postgres psql -U scraper_user -d scraper_db < "$migration" 2>/dev/null || true
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

sleep 5

if curl -sf http://localhost:8000/health > /dev/null; then
    print_success "API Scraper-Pro opérationnelle"
else
    print_warning "API ne répond pas encore (attendre 30s)"
fi

if curl -sf http://localhost:8501 > /dev/null; then
    print_success "Dashboard accessible"
else
    print_warning "Dashboard ne répond pas encore"
fi

# ========================================
# État des ressources
# ========================================

print_header "📊 État des Ressources"

echo ""
echo "🖥️  RAM Système :"
free -h | grep Mem

echo ""
echo "🐳 Containers Scraper-Pro :"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}" | grep scraper

# ========================================
# Récapitulatif
# ========================================

print_header "✅ Déploiement Terminé !"

SERVER_IP=$(hostname -I | awk '{print $1}')

cat <<EOF

${GREEN}🎉 Scraper-Pro est déployé !${NC}

${BLUE}📍 URLs d'accès :${NC}

  🔧 API       : http://$SERVER_IP:8000
  📊 Dashboard : http://$SERVER_IP:8501

  ✅ Health    : http://$SERVER_IP:8000/health

${BLUE}🔐 Credentials :${NC}

  📄 Fichier secrets : ${SECRETS_FILE}

${BLUE}📊 Commandes utiles :${NC}

  # Status des containers
  docker compose -f docker-compose.scraper-only.yml ps

  # Logs en temps réel
  docker compose -f docker-compose.scraper-only.yml logs -f

  # Monitoring RAM
  docker stats

  # Redémarrer
  docker compose -f docker-compose.scraper-only.yml restart

${BLUE}🚀 Premier test :${NC}

  # Créer un job de scraping
  curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \\
    -H "Content-Type: application/json" \\
    -d '{
      "source_type": "custom_urls",
      "name": "Test Expat",
      "config": {"urls": ["https://www.expat.com/fr/guide/"]},
      "max_results": 50
    }'

${GREEN}✅ Installation terminée avec succès !${NC}

========================================

EOF
