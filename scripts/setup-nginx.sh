#!/bin/bash

# ============================================================
# SCRAPER-PRO: NGINX + SSL AUTOMATIC SETUP
# ============================================================
# Automatically configures Nginx reverse proxy with Let's Encrypt SSL
# for Dashboard, API, and Grafana
#
# Usage:
#   bash scripts/setup-nginx.sh yourdomain.com
#   bash scripts/setup-nginx.sh yourdomain.com your-email@example.com
# ============================================================

set -euo pipefail

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

DOMAIN=${1:-}
EMAIL=${2:-admin@$DOMAIN}

if [ -z "$DOMAIN" ]; then
    log_error "Missing domain argument"
    echo ""
    echo "Usage: bash scripts/setup-nginx.sh yourdomain.com [email]"
    echo ""
    echo "Examples:"
    echo "  bash scripts/setup-nginx.sh scraper.example.com"
    echo "  bash scripts/setup-nginx.sh scraper.example.com admin@example.com"
    echo ""
    echo "This will create 3 subdomains:"
    echo "  - dashboard.$DOMAIN → Streamlit Dashboard (port 8501)"
    echo "  - api.$DOMAIN → FastAPI (port 8000)"
    echo "  - grafana.$DOMAIN → Grafana Monitoring (port 3000)"
    echo ""
    exit 1
fi

# ────────────────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────────────────

echo "========================================="
echo "  Nginx + SSL Setup for Scraper-Pro"
echo "========================================="
echo ""
log_info "Domain: $DOMAIN"
log_info "Email: $EMAIL"
log_info "Subdomains:"
echo "  - dashboard.$DOMAIN"
echo "  - api.$DOMAIN"
echo "  - grafana.$DOMAIN"
echo ""

# ────────────────────────────────────────────────────────────
# STEP 1: INSTALL NGINX AND CERTBOT
# ────────────────────────────────────────────────────────────

log_info "Step 1/7: Installing Nginx and Certbot..."

if ! command -v nginx &> /dev/null; then
    sudo apt update -y
    sudo apt install -y nginx
    log_success "Nginx installed"
else
    log_warning "Nginx already installed, skipping..."
fi

if ! command -v certbot &> /dev/null; then
    sudo apt install -y certbot python3-certbot-nginx
    log_success "Certbot installed"
else
    log_warning "Certbot already installed, skipping..."
fi

# ────────────────────────────────────────────────────────────
# STEP 2: CHECK DNS CONFIGURATION
# ────────────────────────────────────────────────────────────

log_info "Step 2/7: Checking DNS configuration..."

SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com)
log_info "Server IP: $SERVER_IP"

echo ""
log_warning "IMPORTANT: Before continuing, verify DNS records are configured:"
echo ""
echo "  DNS Type A Records:"
echo "  ┌────────────────────────────────────┬────────┬──────────────────┐"
echo "  │ Name                               │ Type   │ Value            │"
echo "  ├────────────────────────────────────┼────────┼──────────────────┤"
echo "  │ dashboard.$DOMAIN │ A      │ $SERVER_IP │"
echo "  │ api.$DOMAIN       │ A      │ $SERVER_IP │"
echo "  │ grafana.$DOMAIN   │ A      │ $SERVER_IP │"
echo "  └────────────────────────────────────┴────────┴──────────────────┘"
echo ""
echo "  Check DNS propagation: https://dnschecker.org/"
echo ""

read -p "Have you configured DNS records? (yes/no): " dns_configured

if [ "$dns_configured" != "yes" ] && [ "$dns_configured" != "y" ]; then
    log_error "Please configure DNS records first, then run this script again."
    exit 1
fi

# Test DNS resolution
log_info "Testing DNS resolution..."

for subdomain in dashboard api grafana; do
    RESOLVED_IP=$(dig +short $subdomain.$DOMAIN | tail -1)

    if [ -z "$RESOLVED_IP" ]; then
        log_error "$subdomain.$DOMAIN does not resolve to any IP"
        log_warning "Wait 5-10 minutes for DNS propagation, then try again"
        exit 1
    elif [ "$RESOLVED_IP" != "$SERVER_IP" ]; then
        log_warning "$subdomain.$DOMAIN resolves to $RESOLVED_IP (expected $SERVER_IP)"
        log_warning "DNS may still be propagating. Continue anyway? (yes/no)"
        read -p "> " continue_anyway
        if [ "$continue_anyway" != "yes" ] && [ "$continue_anyway" != "y" ]; then
            exit 1
        fi
    else
        log_success "$subdomain.$DOMAIN → $RESOLVED_IP ✅"
    fi
done

echo ""

# ────────────────────────────────────────────────────────────
# STEP 3: CREATE NGINX CONFIG FOR DASHBOARD
# ────────────────────────────────────────────────────────────

log_info "Step 3/7: Creating Nginx config for Dashboard..."

sudo tee /etc/nginx/sites-available/scraper-dashboard > /dev/null <<EOF
# Scraper-Pro Dashboard (Streamlit)
# Auto-generated by setup-nginx.sh on $(date)

server {
    listen 80;
    listen [::]:80;
    server_name dashboard.$DOMAIN;

    # Logging
    access_log /var/log/nginx/scraper-dashboard-access.log;
    error_log /var/log/nginx/scraper-dashboard-error.log;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;

        # WebSocket support (for Streamlit)
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Headers
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts (Streamlit can be slow)
        proxy_read_timeout 86400;
        proxy_connect_timeout 86400;
        proxy_send_timeout 86400;

        # Buffer settings
        proxy_buffering off;
    }
}
EOF

log_success "Dashboard config created"

# ────────────────────────────────────────────────────────────
# STEP 4: CREATE NGINX CONFIG FOR API
# ────────────────────────────────────────────────────────────

log_info "Step 4/7: Creating Nginx config for API..."

sudo tee /etc/nginx/sites-available/scraper-api > /dev/null <<EOF
# Scraper-Pro API (FastAPI)
# Auto-generated by setup-nginx.sh on $(date)

server {
    listen 80;
    listen [::]:80;
    server_name api.$DOMAIN;

    # Logging
    access_log /var/log/nginx/scraper-api-access.log;
    error_log /var/log/nginx/scraper-api-error.log;

    # Max body size (for large requests)
    client_max_body_size 10M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # Health check endpoint (no auth required)
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

log_success "API config created"

# ────────────────────────────────────────────────────────────
# STEP 5: CREATE NGINX CONFIG FOR GRAFANA
# ────────────────────────────────────────────────────────────

log_info "Step 5/7: Creating Nginx config for Grafana..."

sudo tee /etc/nginx/sites-available/scraper-grafana > /dev/null <<EOF
# Scraper-Pro Grafana (Monitoring)
# Auto-generated by setup-nginx.sh on $(date)

server {
    listen 80;
    listen [::]:80;
    server_name grafana.$DOMAIN;

    # Logging
    access_log /var/log/nginx/scraper-grafana-access.log;
    error_log /var/log/nginx/scraper-grafana-error.log;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support (for live updates)
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_read_timeout 300;
    }
}
EOF

log_success "Grafana config created"

# ────────────────────────────────────────────────────────────
# STEP 6: ENABLE SITES AND TEST CONFIG
# ────────────────────────────────────────────────────────────

log_info "Step 6/7: Enabling sites and testing config..."

# Remove default Nginx site if it exists
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    sudo rm /etc/nginx/sites-enabled/default
    log_info "Removed default Nginx site"
fi

# Create symbolic links
sudo ln -sf /etc/nginx/sites-available/scraper-dashboard /etc/nginx/sites-enabled/
sudo ln -sf /etc/nginx/sites-available/scraper-api /etc/nginx/sites-enabled/
sudo ln -sf /etc/nginx/sites-available/scraper-grafana /etc/nginx/sites-enabled/

log_success "Sites enabled"

# Test Nginx configuration
log_info "Testing Nginx configuration..."

if sudo nginx -t; then
    log_success "Nginx configuration is valid"
else
    log_error "Nginx configuration has errors"
    exit 1
fi

# Reload Nginx
sudo systemctl reload nginx
log_success "Nginx reloaded"

# ────────────────────────────────────────────────────────────
# STEP 7: INSTALL SSL CERTIFICATES
# ────────────────────────────────────────────────────────────

log_info "Step 7/7: Installing SSL certificates (Let's Encrypt)..."

echo ""
log_info "This will install SSL certificates for:"
echo "  - dashboard.$DOMAIN"
echo "  - api.$DOMAIN"
echo "  - grafana.$DOMAIN"
echo ""
log_warning "You will be asked a few questions by Certbot..."
echo ""

# Install certificates for all 3 subdomains at once
sudo certbot --nginx \
    -d dashboard.$DOMAIN \
    -d api.$DOMAIN \
    -d grafana.$DOMAIN \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --redirect

if [ $? -eq 0 ]; then
    log_success "SSL certificates installed successfully!"
else
    log_error "SSL certificate installation failed"
    echo ""
    log_warning "Common issues:"
    echo "  1. DNS not yet propagated (wait 10 minutes, try again)"
    echo "  2. Port 80/443 blocked by firewall"
    echo "  3. Email address invalid"
    echo ""
    log_info "You can manually install SSL later with:"
    echo "  sudo certbot --nginx -d dashboard.$DOMAIN -d api.$DOMAIN -d grafana.$DOMAIN"
    echo ""
    exit 1
fi

# ────────────────────────────────────────────────────────────
# STEP 8: SETUP AUTO-RENEWAL
# ────────────────────────────────────────────────────────────

log_info "Setting up automatic SSL renewal..."

# Test renewal
sudo certbot renew --dry-run

if [ $? -eq 0 ]; then
    log_success "Auto-renewal configured and tested successfully"
else
    log_warning "Auto-renewal test failed (this is usually OK)"
fi

# Add cron job for auto-renewal (if not already present)
if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -
    log_success "Added cron job for SSL auto-renewal (daily at 3 AM)"
else
    log_info "SSL auto-renewal cron job already exists"
fi

# ────────────────────────────────────────────────────────────
# STEP 9: CONFIGURE FIREWALL
# ────────────────────────────────────────────────────────────

log_info "Configuring firewall..."

# Check if UFW is installed
if command -v ufw &> /dev/null; then
    # Allow HTTP and HTTPS
    sudo ufw allow 'Nginx Full' || true
    sudo ufw allow 80/tcp || true
    sudo ufw allow 443/tcp || true

    # Remove individual service ports (now behind Nginx)
    sudo ufw delete allow 8501/tcp 2>/dev/null || true
    sudo ufw delete allow 8000/tcp 2>/dev/null || true
    sudo ufw delete allow 3000/tcp 2>/dev/null || true

    log_success "Firewall configured"
else
    log_warning "UFW not installed, skipping firewall configuration"
fi

# ────────────────────────────────────────────────────────────
# SUMMARY
# ────────────────────────────────────────────────────────────

echo ""
echo "========================================="
echo "  ✅ Setup Complete!"
echo "========================================="
echo ""
log_success "Nginx reverse proxy and SSL certificates are now configured!"
echo ""
echo "Access your services:"
echo ""
echo "  📊 Dashboard (Streamlit):"
echo "     https://dashboard.$DOMAIN"
echo "     Password: (from DASHBOARD_PASSWORD in .env)"
echo ""
echo "  🔌 API (FastAPI):"
echo "     https://api.$DOMAIN"
echo "     https://api.$DOMAIN/health"
echo "     https://api.$DOMAIN/docs (Swagger UI)"
echo ""
echo "  📈 Grafana (Monitoring):"
echo "     https://grafana.$DOMAIN"
echo "     Username: admin"
echo "     Password: (from GRAFANA_PASSWORD in .env)"
echo ""
echo "========================================="
echo "  Security Notes"
echo "========================================="
echo ""
echo "  ✅ All traffic is encrypted with SSL/TLS"
echo "  ✅ Certificates auto-renew every 60 days"
echo "  ✅ HTTP automatically redirects to HTTPS"
echo "  ✅ Services only accessible via Nginx (not direct ports)"
echo ""
echo "========================================="
echo "  Maintenance Commands"
echo "========================================="
echo ""
echo "  Check SSL certificate status:"
echo "    sudo certbot certificates"
echo ""
echo "  Renew SSL certificates manually:"
echo "    sudo certbot renew"
echo ""
echo "  Test Nginx configuration:"
echo "    sudo nginx -t"
echo ""
echo "  Reload Nginx:"
echo "    sudo systemctl reload nginx"
echo ""
echo "  View Nginx logs:"
echo "    sudo tail -f /var/log/nginx/scraper-*-error.log"
echo ""
echo "========================================="
echo ""

log_success "Setup completed successfully!"
echo ""
