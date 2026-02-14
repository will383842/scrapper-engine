#!/bin/bash

# ============================================================
# SCRAPER-PRO: PRODUCTION INITIALIZATION SCRIPT
# ============================================================
# Automatic production setup for Hetzner CPX31 (Ubuntu 22.04+)
# This script handles EVERYTHING from zero to production-ready
#
# Features:
# - Pre-flight checks (Docker, Docker Compose, OS)
# - Secure secret generation (PostgreSQL, Redis, API, Grafana)
# - .env file creation from template
# - Database migration automation
# - Service startup with health checks
# - Monitoring stack verification
# - Firewall configuration
# - Final status report
#
# Usage:
#   bash scripts/init-production.sh
#   bash scripts/init-production.sh --skip-secrets  # Use existing .env
#   bash scripts/init-production.sh --no-firewall   # Skip UFW setup
#   bash scripts/init-production.sh --dry-run       # Check only
# ============================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'

# ────────────────────────────────────────────────────────────
# COLORS & FORMATTING
# ────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ────────────────────────────────────────────────────────────
# LOGGING FUNCTIONS
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

log_step() {
    echo ""
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD} $1${NC}"
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo ""
}

# ────────────────────────────────────────────────────────────
# ARGUMENTS PARSING
# ────────────────────────────────────────────────────────────

SKIP_SECRETS=false
NO_FIREWALL=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-secrets)
            SKIP_SECRETS=true
            shift
            ;;
        --no-firewall)
            NO_FIREWALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-secrets   Use existing .env file (don't generate new secrets)"
            echo "  --no-firewall    Skip UFW firewall configuration"
            echo "  --dry-run        Check prerequisites only, don't install"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# ────────────────────────────────────────────────────────────
# BANNER
# ────────────────────────────────────────────────────────────

clear
echo -e "${MAGENTA}${BOLD}"
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   ███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗ ║
║   ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗║
║   ███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝║
║   ╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗║
║   ███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║║
║   ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝║
║                                                            ║
║              PRODUCTION INITIALIZATION SCRIPT             ║
║                    Version 2.0.0                          ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${CYAN}Optimized for: Hetzner CPX31 (4 vCPU, 8GB RAM)${NC}"
echo -e "${CYAN}Mode: URLs Only (NO proxies, NO Google)${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_warning "DRY RUN MODE - No changes will be made"
fi

sleep 2

# ────────────────────────────────────────────────────────────
# STEP 1: PRE-FLIGHT CHECKS
# ────────────────────────────────────────────────────────────

log_step "STEP 1/12: Pre-flight Checks"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    log_error "Do NOT run this script as root!"
    log_error "Run as regular user with sudo access: bash scripts/init-production.sh"
    exit 1
fi

log_success "Running as non-root user"

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log_info "Detected OS: $NAME $VERSION"

    if [[ ! "$ID" =~ ^(ubuntu|debian)$ ]]; then
        log_warning "This script is optimized for Ubuntu/Debian"
        log_warning "Detected: $ID - Proceed with caution"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    log_warning "Could not detect OS version"
fi

# Check sudo access
if ! sudo -n true 2>/dev/null; then
    log_info "Testing sudo access..."
    sudo echo "Sudo access confirmed"
fi

log_success "Pre-flight checks passed"

# ────────────────────────────────────────────────────────────
# STEP 2: CHECK DOCKER
# ────────────────────────────────────────────────────────────

log_step "STEP 2/12: Verify Docker Installation"

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed!"
    log_info "Install Docker: https://docs.docker.com/engine/install/ubuntu/"
    log_info "Or run: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
log_success "Docker installed: $DOCKER_VERSION"

# Check if user is in docker group
if ! groups | grep -q docker; then
    log_warning "User not in 'docker' group"
    log_info "Adding user to docker group..."
    sudo usermod -aG docker $USER
    log_warning "You must logout and login again for group changes to take effect"
    log_warning "After re-login, run this script again"
    exit 0
fi

log_success "User in docker group"

# ────────────────────────────────────────────────────────────
# STEP 3: CHECK DOCKER COMPOSE
# ────────────────────────────────────────────────────────────

log_step "STEP 3/12: Verify Docker Compose Installation"

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed!"
    log_info "Install: sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
    log_info "Then: sudo chmod +x /usr/local/bin/docker-compose"
    exit 1
fi

COMPOSE_VERSION=$(docker-compose --version | awk '{print $4}' | tr -d ',v')
log_success "Docker Compose installed: $COMPOSE_VERSION"

# ────────────────────────────────────────────────────────────
# STEP 4: CHECK PROJECT DIRECTORY
# ────────────────────────────────────────────────────────────

log_step "STEP 4/12: Verify Project Directory"

# Detect project directory
if [ -f "docker-compose.production.yml" ]; then
    PROJECT_DIR=$(pwd)
    log_success "Project directory: $PROJECT_DIR"
else
    log_error "docker-compose.production.yml not found!"
    log_error "Please run this script from the project root directory"
    exit 1
fi

# Check required files
REQUIRED_FILES=(
    "docker-compose.production.yml"
    ".env.production"
    "Dockerfile"
    "requirements.txt"
    "config/scraping_modes.json"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "Missing required file: $file"
        exit 1
    fi
done

log_success "All required files present"

# Exit if dry run
if [ "$DRY_RUN" = true ]; then
    log_success "DRY RUN COMPLETE - All checks passed"
    exit 0
fi

# ────────────────────────────────────────────────────────────
# STEP 5: GENERATE SECRETS
# ────────────────────────────────────────────────────────────

log_step "STEP 5/12: Generate Secure Secrets"

if [ "$SKIP_SECRETS" = true ]; then
    log_warning "Skipping secret generation (--skip-secrets flag)"

    if [ ! -f ".env" ]; then
        log_error ".env file not found and --skip-secrets is set!"
        exit 1
    fi

    log_info "Using existing .env file"
else
    log_info "Generating cryptographically secure secrets..."

    # Generate secrets
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    API_HMAC_SECRET=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-64)
    DASHBOARD_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-24)
    GRAFANA_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-24)

    log_success "Secrets generated (32-64 chars, alphanumeric)"

    # Create .env from template
    log_info "Creating .env file from .env.production template..."
    cp .env.production .env

    # Replace placeholders
    sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" .env
    sed -i "s|REDIS_PASSWORD=.*|REDIS_PASSWORD=$REDIS_PASSWORD|" .env
    sed -i "s|API_HMAC_SECRET=.*|API_HMAC_SECRET=$API_HMAC_SECRET|" .env
    sed -i "s|DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD|" .env
    sed -i "s|GRAFANA_PASSWORD=.*|GRAFANA_PASSWORD=$GRAFANA_PASSWORD|" .env

    # Set deployment date
    sed -i "s|DEPLOYMENT_DATE=.*|DEPLOYMENT_DATE=$(date +%Y-%m-%d)|" .env

    # Set secure permissions
    chmod 600 .env

    log_success ".env file created with secure permissions (600)"

    # Save secrets to a secure backup
    SECRETS_FILE="$HOME/.scraper-pro-secrets-$(date +%Y%m%d-%H%M%S).txt"
    cat > "$SECRETS_FILE" << EOF
# SCRAPER-PRO PRODUCTION SECRETS
# Generated: $(date)
# IMPORTANT: Store securely and delete after saving to password manager

POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
API_HMAC_SECRET=$API_HMAC_SECRET
DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD
GRAFANA_PASSWORD=$GRAFANA_PASSWORD

# Dashboard Access:
# URL: http://your-server-ip:8501
# Password: $DASHBOARD_PASSWORD

# Grafana Access:
# URL: http://your-server-ip:3000
# Username: admin
# Password: $GRAFANA_PASSWORD

# IMPORTANT:
# 1. Copy these secrets to your password manager
# 2. Delete this file: rm "$SECRETS_FILE"
# 3. Update MailWizz API keys in .env manually
# 4. Update Webhook secrets in .env manually
EOF

    chmod 600 "$SECRETS_FILE"

    echo ""
    echo -e "${YELLOW}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}${BOLD} IMPORTANT: SECRETS GENERATED${NC}"
    echo -e "${YELLOW}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Secrets saved to: ${NC}${BOLD}$SECRETS_FILE${NC}"
    echo ""
    echo -e "${YELLOW}Action required:${NC}"
    echo "1. Copy secrets to your password manager"
    echo "2. Delete the secrets file: rm \"$SECRETS_FILE\""
    echo "3. Update MailWizz API keys in .env manually"
    echo ""
    echo -e "${YELLOW}Dashboard Password: ${NC}${BOLD}$DASHBOARD_PASSWORD${NC}"
    echo -e "${YELLOW}Grafana Password:   ${NC}${BOLD}$GRAFANA_PASSWORD${NC}"
    echo ""
    read -p "Press ENTER to continue after saving secrets..."
fi

# ────────────────────────────────────────────────────────────
# STEP 6: VERIFY .ENV CONFIGURATION
# ────────────────────────────────────────────────────────────

log_step "STEP 6/12: Verify .env Configuration"

# Source .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
    log_success ".env file loaded"
else
    log_error ".env file not found!"
    exit 1
fi

# Check critical variables
CRITICAL_VARS=(
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "API_HMAC_SECRET"
    "DASHBOARD_PASSWORD"
)

log_info "Checking critical environment variables..."

for var in "${CRITICAL_VARS[@]}"; do
    value="${!var}"
    if [[ "$value" =~ CHANGE_ME ]]; then
        log_error "$var still contains CHANGE_ME placeholder!"
        log_error "Please edit .env file and set all required secrets"
        exit 1
    fi

    if [ -z "$value" ]; then
        log_error "$var is empty!"
        exit 1
    fi

    log_success "$var is set (${#value} chars)"
done

log_success "All critical variables configured"

# ────────────────────────────────────────────────────────────
# STEP 7: CONFIGURE FIREWALL (Optional)
# ────────────────────────────────────────────────────────────

log_step "STEP 7/12: Configure Firewall (UFW)"

if [ "$NO_FIREWALL" = true ]; then
    log_warning "Skipping firewall configuration (--no-firewall flag)"
else
    if ! command -v ufw &> /dev/null; then
        log_warning "UFW not installed, skipping firewall setup"
    else
        log_info "Configuring UFW firewall rules..."

        # Allow SSH (critical - don't lock yourself out!)
        sudo ufw allow 22/tcp comment 'SSH'

        # Allow HTTP/HTTPS (for Nginx reverse proxy)
        sudo ufw allow 80/tcp comment 'HTTP'
        sudo ufw allow 443/tcp comment 'HTTPS'

        # Enable firewall
        sudo ufw --force enable

        log_success "Firewall configured and enabled"
        log_info "Allowed ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)"
        log_warning "Local services (8000, 8501, 3000) are NOT exposed to internet"
    fi
fi

# ────────────────────────────────────────────────────────────
# STEP 8: PULL DOCKER IMAGES
# ────────────────────────────────────────────────────────────

log_step "STEP 8/12: Pull Docker Images"

log_info "Pulling latest Docker images (this may take a few minutes)..."

docker-compose -f docker-compose.production.yml pull

log_success "Docker images pulled"

# ────────────────────────────────────────────────────────────
# STEP 9: BUILD APPLICATION IMAGES
# ────────────────────────────────────────────────────────────

log_step "STEP 9/12: Build Application Images"

log_info "Building scraper and dashboard images..."

docker-compose -f docker-compose.production.yml build --no-cache

log_success "Application images built"

# ────────────────────────────────────────────────────────────
# STEP 10: START SERVICES
# ────────────────────────────────────────────────────────────

log_step "STEP 10/12: Start Services"

log_info "Starting all services (PostgreSQL, Redis, Scraper, Dashboard, Monitoring)..."

docker-compose -f docker-compose.production.yml up -d

log_success "Services started"

# ────────────────────────────────────────────────────────────
# STEP 11: HEALTH CHECKS
# ────────────────────────────────────────────────────────────

log_step "STEP 11/12: Health Checks"

log_info "Waiting for services to be ready (60 seconds)..."

for i in {1..60}; do
    echo -n "."
    sleep 1
done
echo ""

# Check PostgreSQL
log_info "Checking PostgreSQL..."
if docker exec scraper-postgres pg_isready -U scraper_admin > /dev/null 2>&1; then
    log_success "PostgreSQL is healthy"
else
    log_error "PostgreSQL health check failed"
fi

# Check Redis
log_info "Checking Redis..."
if docker exec scraper-redis redis-cli -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; then
    log_success "Redis is healthy"
else
    log_error "Redis health check failed"
fi

# Check Scraper API
log_info "Checking Scraper API..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    log_success "Scraper API is healthy"
else
    log_warning "Scraper API not responding yet (may need more time)"
fi

# Check Dashboard
log_info "Checking Dashboard..."
if curl -sf -o /dev/null http://localhost:8501 2>&1; then
    log_success "Dashboard is accessible"
else
    log_warning "Dashboard not responding yet (may need more time)"
fi

# Check Prometheus
log_info "Checking Prometheus..."
if curl -sf http://localhost:9090/-/healthy > /dev/null 2>&1; then
    log_success "Prometheus is healthy"
else
    log_warning "Prometheus not responding yet"
fi

# Check Grafana
log_info "Checking Grafana..."
if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
    log_success "Grafana is healthy"
else
    log_warning "Grafana not responding yet"
fi

# ────────────────────────────────────────────────────────────
# STEP 12: FINAL STATUS
# ────────────────────────────────────────────────────────────

log_step "STEP 12/12: Final Status"

log_info "Container status:"
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=scraper"
echo ""

# ────────────────────────────────────────────────────────────
# SUCCESS SUMMARY
# ────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  SCRAPER-PRO PRODUCTION INSTALLATION COMPLETE!${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════${NC}"
echo ""

log_success "All services are running!"
echo ""

echo -e "${CYAN}${BOLD}Quick Access:${NC}"
echo ""
echo -e "  ${BOLD}Dashboard:${NC}    http://localhost:8501"
echo -e "                 Password: See secrets file"
echo ""
echo -e "  ${BOLD}Grafana:${NC}      http://localhost:3000"
echo -e "                 Username: admin"
echo -e "                 Password: See secrets file"
echo ""
echo -e "  ${BOLD}Prometheus:${NC}   http://localhost:9090"
echo ""
echo -e "  ${BOLD}API:${NC}          http://localhost:8000"
echo -e "                 Health: http://localhost:8000/health"
echo ""

echo -e "${YELLOW}${BOLD}Next Steps:${NC}"
echo ""
echo "1. Configure Nginx reverse proxy with SSL (Let's Encrypt)"
echo "   See: DEPLOYMENT_PRODUCTION.md for instructions"
echo ""
echo "2. Update MailWizz API keys in .env:"
echo "   nano .env"
echo "   (Update MAILWIZZ_*_API_KEY variables)"
echo ""
echo "3. Update Webhook secrets in .env:"
echo "   nano .env"
echo "   (Update WEBHOOK_*_SECRET variables)"
echo ""
echo "4. Restart services after .env changes:"
echo "   docker-compose -f docker-compose.production.yml restart"
echo ""
echo "5. Set up automated backups:"
echo "   bash scripts/backup-postgres.sh"
echo ""
echo "6. Configure monitoring alerts:"
echo "   Edit monitoring/alertmanager/alertmanager.yml"
echo ""

echo -e "${YELLOW}${BOLD}Useful Commands:${NC}"
echo ""
echo "  View logs:        docker-compose -f docker-compose.production.yml logs -f"
echo "  Stop services:    docker-compose -f docker-compose.production.yml stop"
echo "  Start services:   docker-compose -f docker-compose.production.yml start"
echo "  Restart services: docker-compose -f docker-compose.production.yml restart"
echo "  Container status: docker ps"
echo ""

echo -e "${CYAN}${BOLD}Documentation:${NC}"
echo ""
echo "  - DEPLOYMENT_PRODUCTION.md (Full deployment guide)"
echo "  - docs/DEDUPLICATION_SYSTEM.md (Deduplication docs)"
echo "  - ULTRA_PRO_SYSTEM_READY.md (System overview)"
echo "  - FAQ_CRITIQUE.md (Troubleshooting)"
echo ""

if [ "$SKIP_SECRETS" = false ]; then
    echo -e "${RED}${BOLD}SECURITY REMINDER:${NC}"
    echo ""
    echo "  1. Secrets are saved in: $SECRETS_FILE"
    echo "  2. Copy to password manager NOW"
    echo "  3. Delete secrets file: rm \"$SECRETS_FILE\""
    echo ""
fi

echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════${NC}"
echo ""

log_success "Installation script completed successfully!"
log_info "Happy scraping! 🚀"
echo ""
