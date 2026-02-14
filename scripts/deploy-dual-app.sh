#!/bin/bash
# ========================================
# SCRIPT DE DÉPLOIEMENT DUAL-APP
# ========================================
# Déploiement automatique de Scraper-Pro + Backlink Engine
# sur un serveur 2 vCPU / 4 GB RAM
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

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 n'est pas installé"
        return 1
    fi
    print_success "$1 est installé"
    return 0
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
if ! check_command docker; then
    print_warning "Docker n'est pas installé. Installation en cours..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    print_success "Docker installé"
fi

# Vérifier Docker Compose
if ! docker compose version &> /dev/null; then
    print_warning "Docker Compose plugin manquant. Installation en cours..."
    apt-get update
    apt-get install -y docker-compose-plugin
    print_success "Docker Compose installé"
fi

# Vérifier les ressources système
print_header "📊 Ressources Système"

TOTAL_RAM=$(free -m | grep Mem | awk '{print $2}')
TOTAL_CPU=$(nproc)
TOTAL_DISK=$(df -h / | tail -1 | awk '{print $4}')

echo "CPU   : $TOTAL_CPU vCPU"
echo "RAM   : $TOTAL_RAM MB"
echo "Disk  : $TOTAL_DISK disponible"

if [ "$TOTAL_RAM" -lt 3500 ]; then
    print_warning "RAM < 4 GB détectée. Recommandé : 4 GB minimum"
    read -p "Continuer quand même ? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_success "Ressources système suffisantes"

# ========================================
# Configuration du projet
# ========================================

print_header "⚙️  Configuration du Projet"

# Déterminer le répertoire du projet
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

print_info "Répertoire du projet : $PROJECT_DIR"

# Vérifier que docker-compose.optimized.yml existe
if [ ! -f "docker-compose.optimized.yml" ]; then
    print_error "docker-compose.optimized.yml introuvable"
    exit 1
fi

print_success "Fichier docker-compose.optimized.yml trouvé"

# ========================================
# Génération des secrets
# ========================================

print_header "🔐 Génération des Secrets"

if [ ! -f ".env" ]; then
    print_info "Création du fichier .env depuis .env.optimized"
    cp .env.optimized .env
fi

# Fonction pour générer un secret
generate_secret() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Remplacer les secrets si nécessaire
if grep -q "CHANGE_ME" .env; then
    print_info "Génération de nouveaux secrets..."

    POSTGRES_PASSWORD=$(generate_secret)
    REDIS_PASSWORD=$(generate_secret)
    API_HMAC_SECRET=$(generate_secret)
    DASHBOARD_PASSWORD=$(generate_secret)
    APP_KEY="base64:$(openssl rand -base64 32)"

    sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" .env
    sed -i "s|REDIS_PASSWORD=.*|REDIS_PASSWORD=$REDIS_PASSWORD|" .env
    sed -i "s|API_HMAC_SECRET=.*|API_HMAC_SECRET=$API_HMAC_SECRET|" .env
    sed -i "s|DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD|" .env
    sed -i "s|APP_KEY=.*|APP_KEY=$APP_KEY|" .env

    print_success "Secrets générés et sauvegardés dans .env"

    # Sauvegarder les secrets dans un fichier sécurisé
    SECRETS_FILE="$HOME/.scraper-secrets-$(date +%Y%m%d_%H%M%S).txt"
    cat > "$SECRETS_FILE" <<EOF
========================================
SECRETS GÉNÉRÉS - $(date)
========================================

POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
API_HMAC_SECRET=$API_HMAC_SECRET
DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD
APP_KEY=$APP_KEY

========================================
IMPORTANT : Sauvegarder ce fichier dans un endroit sûr !
Fichier : $SECRETS_FILE
========================================
EOF

    chmod 600 "$SECRETS_FILE"
    print_success "Secrets sauvegardés dans $SECRETS_FILE"
else
    print_info "Secrets déjà configurés dans .env"
fi

# ========================================
# Préparation PostgreSQL init script
# ========================================

print_header "📦 Préparation des Scripts"

if [ -f "scripts/postgres-init.sh" ]; then
    chmod +x scripts/postgres-init.sh
    print_success "Script postgres-init.sh configuré"
else
    print_warning "scripts/postgres-init.sh introuvable"
fi

# ========================================
# Arrêt des services existants (si redéploiement)
# ========================================

print_header "🛑 Arrêt des Services Existants"

if docker compose -f docker-compose.optimized.yml ps --quiet | grep -q .; then
    print_info "Services existants détectés. Arrêt en cours..."
    docker compose -f docker-compose.optimized.yml down
    print_success "Services arrêtés"
else
    print_info "Aucun service existant à arrêter"
fi

# ========================================
# Construction des images Docker
# ========================================

print_header "🏗️  Construction des Images Docker"

docker compose -f docker-compose.optimized.yml build --no-cache

print_success "Images Docker construites"

# ========================================
# Démarrage des services
# ========================================

print_header "🚀 Démarrage des Services"

docker compose -f docker-compose.optimized.yml up -d

# Attendre que PostgreSQL soit prêt
print_info "Attente du démarrage de PostgreSQL..."
sleep 10

# Vérifier que PostgreSQL est prêt
MAX_RETRIES=30
RETRY_COUNT=0

while ! docker exec shared-postgres pg_isready -U shared_user &> /dev/null; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -gt $MAX_RETRIES ]; then
        print_error "PostgreSQL n'a pas démarré après ${MAX_RETRIES} tentatives"
        exit 1
    fi
    echo -n "."
    sleep 2
done

echo ""
print_success "PostgreSQL est prêt"

# Vérifier que Redis est prêt
print_info "Vérification de Redis..."
if docker exec shared-redis redis-cli ping &> /dev/null; then
    print_success "Redis est prêt"
else
    print_warning "Redis ne répond pas encore"
fi

# ========================================
# Vérification des bases de données
# ========================================

print_header "🗄️  Vérification des Bases de Données"

# Lister les bases
DATABASES=$(docker exec shared-postgres psql -U shared_user -t -c "SELECT datname FROM pg_database WHERE datname IN ('scraper_db', 'backlink_db');")

if echo "$DATABASES" | grep -q "scraper_db"; then
    print_success "Base scraper_db créée"
else
    print_error "Base scraper_db manquante"
fi

if echo "$DATABASES" | grep -q "backlink_db"; then
    print_success "Base backlink_db créée"
else
    print_error "Base backlink_db manquante"
fi

# ========================================
# Application des migrations Scraper-Pro
# ========================================

print_header "📊 Application des Migrations Scraper-Pro"

if [ -d "db/migrations" ]; then
    print_info "Application des migrations SQL..."

    for migration in db/migrations/*.sql; do
        if [ -f "$migration" ]; then
            filename=$(basename "$migration")
            print_info "Application de $filename..."
            docker exec -i shared-postgres psql -U shared_user -d scraper_db < "$migration"
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

# Vérifier l'API Scraper-Pro
print_info "Vérification de l'API Scraper-Pro (port 8000)..."
sleep 5

if curl -sf http://localhost:8000/health > /dev/null; then
    print_success "API Scraper-Pro opérationnelle"
else
    print_warning "API Scraper-Pro ne répond pas encore (normal si premier démarrage)"
fi

# Vérifier le Dashboard
print_info "Vérification du Dashboard (port 8501)..."
if curl -sf http://localhost:8501 > /dev/null; then
    print_success "Dashboard Scraper-Pro accessible"
else
    print_warning "Dashboard ne répond pas encore"
fi

# ========================================
# Monitoring RAM
# ========================================

print_header "📊 État des Ressources"

echo ""
echo "🖥️  RAM Système :"
free -h | grep Mem

echo ""
echo "🐳 Docker Containers :"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}"

# ========================================
# Configuration Firewall (Optionnel)
# ========================================

print_header "🔥 Configuration Firewall (Optionnel)"

read -p "Voulez-vous configurer le firewall UFW ? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    if ! command -v ufw &> /dev/null; then
        apt-get install -y ufw
    fi

    # Autoriser SSH
    ufw allow 22/tcp

    # Demander l'IP de confiance
    read -p "Entrez votre IP de bureau pour accès sécurisé (ou 'skip' pour tout autoriser) : " USER_IP

    if [ "$USER_IP" != "skip" ]; then
        ufw allow from "$USER_IP" to any port 8000
        ufw allow from "$USER_IP" to any port 8501
        ufw allow from "$USER_IP" to any port 8080
        print_success "Firewall configuré pour IP : $USER_IP"
    else
        ufw allow 8000/tcp
        ufw allow 8501/tcp
        ufw allow 8080/tcp
        print_warning "Tous les ports applicatifs sont publics"
    fi

    ufw --force enable
    print_success "Firewall UFW activé"
fi

# ========================================
# Récapitulatif Final
# ========================================

print_header "✅ Déploiement Terminé !"

SERVER_IP=$(hostname -I | awk '{print $1}')

cat <<EOF

${GREEN}🎉 Vos applications sont déployées !${NC}

${BLUE}📍 URLs d'accès :${NC}

  🔧 Scraper-Pro API       : http://$SERVER_IP:8000
  📊 Scraper-Pro Dashboard : http://$SERVER_IP:8501
  🌐 Backlink Engine       : http://$SERVER_IP:8080

  ✅ Health Check API      : http://$SERVER_IP:8000/health
  📋 Logs PostgreSQL       : docker logs shared-postgres
  📋 Logs Scraper Worker   : docker logs scraper-worker

${BLUE}🔐 Credentials :${NC}

  📄 Secrets sauvegardés dans : $SECRETS_FILE
  🔑 Dashboard Password       : Voir $SECRETS_FILE

${BLUE}📊 Commandes utiles :${NC}

  # Voir les containers
  docker compose -f docker-compose.optimized.yml ps

  # Logs en temps réel
  docker compose -f docker-compose.optimized.yml logs -f

  # Monitoring RAM
  docker stats --no-stream

  # Redémarrer un service
  docker compose -f docker-compose.optimized.yml restart scraper-worker

  # Arrêter tous les services
  docker compose -f docker-compose.optimized.yml down

${BLUE}🚀 Prochaines étapes :${NC}

  1. Tester l'API : curl http://$SERVER_IP:8000/health
  2. Accéder au Dashboard : http://$SERVER_IP:8501
  3. Créer un premier job de scraping (voir docs/API_QUICKSTART.md)
  4. Monitorer la RAM avec : watch -n 5 'docker stats --no-stream'

${YELLOW}⚠️  IMPORTANT :${NC}

  • Sauvegarder $SECRETS_FILE dans un endroit sûr !
  • Configurer les backups PostgreSQL (cron)
  • Monitorer la RAM régulièrement

${GREEN}Documentation complète : docs/DUAL_APP_SETUP.md${NC}

========================================

EOF

print_success "Déploiement terminé avec succès !"
