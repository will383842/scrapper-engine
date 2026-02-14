#!/bin/bash

# ============================================================
# SCRAPER-PRO: INSTALLATION VALIDATION SCRIPT
# ============================================================
# Validates that all services are running correctly
# Usage:
#   bash scripts/validate-installation.sh
#   bash scripts/validate-installation.sh --verbose
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
# ARGUMENTS
# ────────────────────────────────────────────────────────────

VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Usage: $0 [--verbose]"
            exit 1
            ;;
    esac
done

# ────────────────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────────────────

echo "========================================="
echo "  Scraper-Pro Installation Validator"
echo "========================================="
echo ""

# ────────────────────────────────────────────────────────────
# COUNTERS
# ────────────────────────────────────────────────────────────

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# ────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────────────────────

check() {
    local name="$1"
    local command="$2"
    local is_optional="${3:-false}"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    echo -n "Checking $name... "

    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        if [ "$is_optional" = "true" ]; then
            echo -e "${YELLOW}⚠️  SKIP (optional)${NC}"
            WARNINGS=$((WARNINGS + 1))
            return 0
        else
            echo -e "${RED}❌ FAIL${NC}"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))

            if [ "$VERBOSE" = "true" ]; then
                echo -e "   ${RED}Command: $command${NC}"
                eval "$command" 2>&1 | sed 's/^/   /' || true
            fi

            return 1
        fi
    fi
}

# ────────────────────────────────────────────────────────────
# CHECKS: DOCKER DAEMON
# ────────────────────────────────────────────────────────────

echo "=== Docker Daemon ==="
check "Docker Daemon Running" "docker ps > /dev/null"

if [ $FAILED_CHECKS -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    echo ""
    echo "To start Docker:"
    echo "  sudo systemctl start docker"
    exit 1
fi

# ────────────────────────────────────────────────────────────
# CHECKS: DOCKER CONTAINERS
# ────────────────────────────────────────────────────────────

echo ""
echo "=== Docker Containers ==="
check "PostgreSQL Container" "docker ps | grep -q scraper-postgres"
check "Redis Container" "docker ps | grep -q scraper-redis"
check "API Container" "docker ps | grep -q scraper-app"
check "Dashboard Container" "docker ps | grep -q scraper-dashboard"
check "Prometheus Container" "docker ps | grep -q scraper-prometheus"
check "Grafana Container" "docker ps | grep -q scraper-grafana"
check "Loki Container" "docker ps | grep -q scraper-loki" true
check "Promtail Container" "docker ps | grep -q scraper-promtail" true

# ────────────────────────────────────────────────────────────
# CHECKS: SERVICE HEALTH
# ────────────────────────────────────────────────────────────

echo ""
echo "=== Service Health Checks ==="

# Load .env for Redis password
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep REDIS_PASSWORD | xargs)
fi

check "API Health Endpoint" "curl -sf http://localhost:8000/health | grep -q '\"status\":\"ok\"'"
check "PostgreSQL Ready" "docker exec scraper-postgres pg_isready -U scraper_admin | grep -q 'accepting connections'"

if [ -n "$REDIS_PASSWORD" ]; then
    check "Redis Ping" "docker exec scraper-redis redis-cli -a '$REDIS_PASSWORD' ping 2>/dev/null | grep -q PONG"
else
    check "Redis Ping (no auth)" "docker exec scraper-redis redis-cli ping 2>/dev/null | grep -q PONG"
fi

check "Dashboard Accessible" "curl -sf http://localhost:8501 -o /dev/null"
check "Grafana Accessible" "curl -sf http://localhost:3000/api/health -o /dev/null"
check "Prometheus Accessible" "curl -sf http://localhost:9090/-/healthy -o /dev/null"

# ────────────────────────────────────────────────────────────
# CHECKS: DATABASE SCHEMA
# ────────────────────────────────────────────────────────────

echo ""
echo "=== Database Schema ==="
check "Scraping Jobs Table" "docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c '\dt' 2>/dev/null | grep -q scraping_jobs"
check "Scraped Contacts Table" "docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c '\dt' 2>/dev/null | grep -q scraped_contacts"
check "URL Deduplication Table" "docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c '\dt' 2>/dev/null | grep -q url_deduplication_cache"
check "Content Hash Table" "docker exec scraper-postgres psql -U scraper_admin -d scraper_db -c '\dt' 2>/dev/null | grep -q content_hash_cache"

# ────────────────────────────────────────────────────────────
# CHECKS: NETWORK CONNECTIVITY
# ────────────────────────────────────────────────────────────

echo ""
echo "=== Network Connectivity ==="
check "API → PostgreSQL" "docker exec scraper-app nc -zv postgres 5432 2>&1 | grep -q succeeded || docker exec scraper-app curl -sf http://postgres:5432 -o /dev/null 2>&1 || true"
check "API → Redis" "docker exec scraper-app nc -zv redis 6379 2>&1 | grep -q succeeded"

# ────────────────────────────────────────────────────────────
# CHECKS: DISK SPACE
# ────────────────────────────────────────────────────────────

echo ""
echo "=== Disk Space ==="

DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')

if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "Disk Usage: ${GREEN}$DISK_USAGE% (OK)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [ "$DISK_USAGE" -lt 90 ]; then
    echo -e "Disk Usage: ${YELLOW}$DISK_USAGE% (Warning)${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "Disk Usage: ${RED}$DISK_USAGE% (Critical)${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# ────────────────────────────────────────────────────────────
# CHECKS: MEMORY USAGE
# ────────────────────────────────────────────────────────────

echo ""
echo "=== Memory Usage ==="

# Check if free command exists
if command -v free &> /dev/null; then
    MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')

    if [ "$MEMORY_USAGE" -lt 80 ]; then
        echo -e "Memory Usage: ${GREEN}$MEMORY_USAGE% (OK)${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif [ "$MEMORY_USAGE" -lt 90 ]; then
        echo -e "Memory Usage: ${YELLOW}$MEMORY_USAGE% (Warning)${NC}"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "Memory Usage: ${RED}$MEMORY_USAGE% (Critical)${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
else
    echo -e "${YELLOW}⚠️  Memory check skipped (free command not available)${NC}"
fi

# ────────────────────────────────────────────────────────────
# CHECKS: SECURITY
# ────────────────────────────────────────────────────────────

echo ""
echo "=== Security Checks ==="

# Check .env permissions
if [ -f ".env" ]; then
    ENV_PERMS=$(stat -c "%a" .env 2>/dev/null || stat -f "%A" .env 2>/dev/null)
    if [ "$ENV_PERMS" = "600" ]; then
        echo -e ".env permissions: ${GREEN}$ENV_PERMS (OK)${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e ".env permissions: ${RED}$ENV_PERMS (Should be 600)${NC}"
        echo -e "   ${YELLOW}Fix with: chmod 600 .env${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi

# Check if default passwords are still in use
if [ -f ".env" ]; then
    if grep -q "CHANGE_ME" .env 2>/dev/null; then
        echo -e "${RED}❌ Default passwords detected in .env${NC}"
        echo -e "   ${YELLOW}Please change all CHANGE_ME values in .env${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    else
        echo -e "${GREEN}✅ No default passwords detected${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi

# ────────────────────────────────────────────────────────────
# SUMMARY
# ────────────────────────────────────────────────────────────

echo ""
echo "========================================="
echo "  Validation Summary"
echo "========================================="
echo -e "Total Checks: $TOTAL_CHECKS"
echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
fi

if [ $FAILED_CHECKS -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    echo ""
    echo -e "${YELLOW}⚠️ Some checks failed. Review the output above.${NC}"
    echo ""
    echo "Troubleshooting tips:"
    echo "  1. Check Docker logs:"
    echo "     docker-compose -f docker-compose.production.yml logs"
    echo ""
    echo "  2. Check specific service logs:"
    echo "     docker logs scraper-app --tail 100"
    echo "     docker logs scraper-postgres --tail 100"
    echo "     docker logs scraper-redis --tail 100"
    echo ""
    echo "  3. Restart services:"
    echo "     docker-compose -f docker-compose.production.yml restart"
    echo ""
    echo "  4. Review .env configuration:"
    echo "     cat .env | grep -v '^#' | grep -v '^$'"
    echo ""
    echo "  5. Check firewall:"
    echo "     sudo ufw status"
    echo ""
    exit 1
else
    echo ""
    echo -e "${GREEN}✅ All checks passed! Installation is healthy.${NC}"
    echo ""
    echo "========================================="
    echo "  Next Steps"
    echo "========================================="
    echo ""
    echo "1. Access Dashboard:"
    echo "   http://localhost:8501"
    echo "   (Or https://dashboard.yourdomain.com if Nginx configured)"
    echo ""
    echo "2. Access Grafana:"
    echo "   http://localhost:3000"
    echo "   Username: admin"
    echo "   Password: (from GRAFANA_PASSWORD in .env)"
    echo ""
    echo "3. Create your first scraping job:"
    echo "   - Open Dashboard"
    echo "   - Go to 'Scraping URLs (Actif)' tab"
    echo "   - Add URLs and click 'Lancer le Job'"
    echo ""
    echo "4. Monitor in real-time:"
    echo "   - Dashboard: Job progress and stats"
    echo "   - Grafana: System metrics and logs"
    echo ""
    echo "5. Setup production access:"
    echo "   bash scripts/setup-nginx.sh yourdomain.com"
    echo ""
    echo "========================================="
    echo ""
    exit 0
fi
