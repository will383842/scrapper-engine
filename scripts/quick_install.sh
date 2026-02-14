#!/bin/bash

# ============================================================
# SCRAPER-PRO: QUICK INSTALL SCRIPT
# ============================================================
# Ce script automatise l'installation complète sur un serveur
# Hetzner CPX31 (Ubuntu 22.04 / Debian 12)
#
# Usage:
#   bash scripts/quick_install.sh
#   bash scripts/quick_install.sh --skip-docker
#   bash scripts/quick_install.sh --cleanup
# ============================================================

set -e  # Exit on error

# ────────────────────────────────────────────────────────────
# COLORS
# ────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ────────────────────────────────────────────────────────────
# FUNCTIONS
# ────────────────────────────────────────────────────────────

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ────────────────────────────────────────────────────────────
# ARGUMENTS
# ────────────────────────────────────────────────────────────

SKIP_DOCKER=false
CLEANUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --cleanup)
            CLEANUP=true
            shift
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "Usage: $0 [--skip-docker] [--cleanup]"
            exit 1
            ;;
    esac
done

# ────────────────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────────────────

echo "============================================================"
echo "  SCRAPER-PRO: QUICK INSTALL SCRIPT"
echo "============================================================"
echo ""
log_info "Starting installation..."
echo ""

# ────────────────────────────────────────────────────────────
# 1. SYSTEM UPDATE
# ────────────────────────────────────────────────────────────

log_info "Step 1/10: Updating system packages..."
sudo apt update -y
sudo apt upgrade -y
sudo apt autoremove -y
log_success "System updated"

# ────────────────────────────────────────────────────────────
# 2. INSTALL DEPENDENCIES
# ────────────────────────────────────────────────────────────

log_info "Step 2/10: Installing dependencies..."
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    git \
    ufw \
    python3 \
    python3-pip

log_success "Dependencies installed"

# ────────────────────────────────────────────────────────────
# 3. INSTALL DOCKER
# ────────────────────────────────────────────────────────────

if [ "$SKIP_DOCKER" = false ]; then
    log_info "Step 3/10: Installing Docker..."

    if ! command -v docker &> /dev/null; then
        # Add Docker GPG key
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

        # Add Docker repository
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        # Install Docker
        sudo apt update -y
        sudo apt install -y docker-ce docker-ce-cli containerd.io

        # Add user to docker group
        sudo usermod -aG docker $USER

        log_success "Docker installed"
    else
        log_warning "Docker already installed, skipping..."
    fi
else
    log_warning "Skipping Docker installation (--skip-docker flag)"
fi

# ────────────────────────────────────────────────────────────
# 4. INSTALL DOCKER COMPOSE
# ────────────────────────────────────────────────────────────

if [ "$SKIP_DOCKER" = false ]; then
    log_info "Step 4/10: Installing Docker Compose..."

    if ! command -v docker-compose &> /dev/null; then
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose

        log_success "Docker Compose installed"
    else
        log_warning "Docker Compose already installed, skipping..."
    fi
else
    log_warning "Skipping Docker Compose installation (--skip-docker flag)"
fi

# ────────────────────────────────────────────────────────────
# 5. CONFIGURE FIREWALL
# ────────────────────────────────────────────────────────────

log_info "Step 5/10: Configuring firewall (UFW)..."

sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS

# Enable firewall (non-interactive)
sudo ufw --force enable

log_success "Firewall configured"

# ────────────────────────────────────────────────────────────
# 6. CLONE PROJECT (if not already cloned)
# ────────────────────────────────────────────────────────────

log_info "Step 6/10: Checking project directory..."

PROJECT_DIR="/home/$USER/scraper-pro"

if [ ! -d "$PROJECT_DIR" ]; then
    log_warning "Project directory not found. Please clone manually:"
    echo ""
    echo "  git clone https://github.com/YOUR_REPO/scraper-pro.git $PROJECT_DIR"
    echo ""
    log_error "Exiting..."
    exit 1
else
    log_success "Project directory found: $PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# ────────────────────────────────────────────────────────────
# 7. SETUP .env
# ────────────────────────────────────────────────────────────

log_info "Step 7/10: Setting up .env file..."

if [ ! -f ".env" ]; then
    log_warning ".env not found. Copying from .env.production..."
    cp .env.production .env

    # ──────────────────────────────────────────────────────
    # AUTO-GÉNÉRATION DES SECRETS (NOUVELLE FONCTIONNALITÉ)
    # ──────────────────────────────────────────────────────

    log_info "Generating secure secrets automatically..."

    # PostgreSQL password (32 caractères)
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    sed -i "s|POSTGRES_PASSWORD=CHANGE_ME_USE_OPENSSL_RAND_BASE64_32|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" .env

    # Redis password (32 caractères)
    REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    sed -i "s|REDIS_PASSWORD=CHANGE_ME_USE_OPENSSL_RAND_BASE64_32|REDIS_PASSWORD=$REDIS_PASSWORD|" .env

    # API HMAC Secret (64 caractères hex)
    API_HMAC_SECRET=$(openssl rand -hex 32)
    sed -i "s|API_HMAC_SECRET=CHANGE_ME_USE_OPENSSL_RAND_BASE64_64_MIN_LENGTH|API_HMAC_SECRET=$API_HMAC_SECRET|" .env

    # Dashboard Password (16 caractères alphanumériques)
    DASHBOARD_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    sed -i "s|DASHBOARD_PASSWORD=CHANGE_ME_STRONG_PASSWORD_16_CHARS_MIN|DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD|" .env

    # Grafana Password (16 caractères alphanumériques)
    GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    sed -i "s|GRAFANA_PASSWORD=CHANGE_ME_STRONG_PASSWORD_GRAFANA|GRAFANA_PASSWORD=$GRAFANA_PASSWORD|" .env

    # Permissions strictes
    chmod 600 .env

    # ──────────────────────────────────────────────────────
    # SAUVEGARDE SÉCURISÉE DES SECRETS
    # ──────────────────────────────────────────────────────

    SECRETS_FILE="$HOME/.scraper-pro-secrets-$(date +%Y%m%d_%H%M%S).txt"
    cat > "$SECRETS_FILE" << EOF
# ============================================================
# Scraper-Pro Secrets - Generated on $(date)
# ============================================================
# ⚠️ KEEP THIS FILE SECURE AND PRIVATE
# ⚠️ NEVER commit to Git or share publicly
# ============================================================

POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
API_HMAC_SECRET=$API_HMAC_SECRET
DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD
GRAFANA_PASSWORD=$GRAFANA_PASSWORD

# ============================================================
# Access URLs (after Nginx setup)
# ============================================================
# Dashboard: https://dashboard.yourdomain.com
#   Username: (no username, just password)
#   Password: $DASHBOARD_PASSWORD
#
# Grafana: https://grafana.yourdomain.com
#   Username: admin
#   Password: $GRAFANA_PASSWORD
#
# API: https://api.yourdomain.com
#   Authentication: HMAC signature with API_HMAC_SECRET
# ============================================================

# IMPORTANT: Store this file in a password manager or encrypted storage
# Suggested locations:
#   - 1Password / LastPass / Bitwarden
#   - Encrypted USB drive
#   - Encrypted cloud storage (Dropbox/Google Drive with encryption)
# ============================================================
EOF

    chmod 600 "$SECRETS_FILE"

    log_success "Secrets generated successfully!"
    echo ""
    log_warning "⚠️ IMPORTANT: Your secrets have been saved to:"
    log_warning "   $SECRETS_FILE"
    echo ""
    log_warning "NEXT STEPS:"
    log_warning "1. Copy this file to a SECURE location (password manager recommended)"
    log_warning "2. Delete the file from the server after saving:"
    log_warning "   rm $SECRETS_FILE"
    log_warning "3. You can still find passwords in: $(pwd)/.env"
    echo ""

else
    log_success ".env already exists, skipping secret generation"
fi

# ────────────────────────────────────────────────────────────
# 8. APPLY DATABASE MIGRATION
# ────────────────────────────────────────────────────────────

log_info "Step 8/10: Preparing database migration..."

if [ -f "db/migrations/001_add_deduplication_tables.sql" ]; then
    log_success "Migration file found"

    # Copy to init directory (will be auto-applied on first start)
    mkdir -p db/init.d
    cp db/migrations/001_add_deduplication_tables.sql db/init.d/

    log_info "Migration will be applied on first PostgreSQL start"
else
    log_warning "Migration file not found, skipping..."
fi

# ────────────────────────────────────────────────────────────
# 9. BUILD & START SERVICES
# ────────────────────────────────────────────────────────────

if [ "$SKIP_DOCKER" = false ]; then
    log_info "Step 9/10: Building and starting services..."

    log_info "Building Docker images..."
    docker-compose -f docker-compose.production.yml build

    log_info "Starting services..."
    docker-compose -f docker-compose.production.yml up -d

    log_info "Waiting for services to be healthy (30s)..."
    sleep 30

    log_success "Services started"
else
    log_warning "Skipping Docker build & start (--skip-docker flag)"
fi

# ────────────────────────────────────────────────────────────
# 10. VERIFY INSTALLATION
# ────────────────────────────────────────────────────────────

log_info "Step 10/10: Verifying installation..."

if [ "$SKIP_DOCKER" = false ]; then
    # Check containers
    log_info "Checking containers..."
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    # Health check API
    log_info "Testing API health..."
    if curl -s http://localhost:8000/health | grep -q "ok"; then
        log_success "API is healthy"
    else
        log_error "API health check failed"
    fi

    # Dashboard check
    log_info "Testing Dashboard..."
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 | grep -q "200"; then
        log_success "Dashboard is accessible"
    else
        log_warning "Dashboard may not be ready yet (wait 1-2 minutes)"
    fi
fi

# ────────────────────────────────────────────────────────────
# CLEANUP (if requested)
# ────────────────────────────────────────────────────────────

if [ "$CLEANUP" = true ]; then
    log_warning "Cleanup mode: removing all data..."

    docker-compose -f docker-compose.production.yml down -v
    sudo rm -rf db/data logs/*

    log_success "Cleanup completed"
fi

# ────────────────────────────────────────────────────────────
# SUMMARY
# ────────────────────────────────────────────────────────────

echo ""
echo "============================================================"
echo "  INSTALLATION COMPLETED"
echo "============================================================"
echo ""

log_success "Scraper-Pro is now installed!"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env with your secrets:"
echo "   nano .env"
echo ""
echo "2. Restart services:"
echo "   docker-compose -f docker-compose.production.yml restart"
echo ""
echo "3. Access Dashboard:"
echo "   http://localhost:8501"
echo ""
echo "4. Access Grafana:"
echo "   http://localhost:3000"
echo "   Username: admin"
echo "   Password: (from GRAFANA_PASSWORD in .env)"
echo ""
echo "5. Run deduplication tests:"
echo "   docker exec scraper-app python scripts/test_deduplication.py"
echo ""
echo "6. Setup Nginx reverse proxy + SSL (see DEPLOYMENT_PRODUCTION.md)"
echo ""
echo "============================================================"
echo ""

log_info "For full documentation, see:"
log_info "  - DEPLOYMENT_PRODUCTION.md (deployment guide)"
log_info "  - docs/DEDUPLICATION_SYSTEM.md (deduplication docs)"
log_info "  - ULTRA_PRO_SYSTEM_READY.md (overview)"
echo ""
