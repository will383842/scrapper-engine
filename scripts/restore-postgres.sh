#!/bin/bash
# ============================================================
# PostgreSQL Restore Script for Scraper-Pro
# ============================================================
# Usage: ./scripts/restore-postgres.sh /path/to/backup.sql.gz
# ============================================================

set -e

# ─── Configuration ──────────────────────────────────────────
POSTGRES_CONTAINER="scraper-postgres"
POSTGRES_USER="scraper_admin"
POSTGRES_DB="scraper_db"

# ─── Colors ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ─── Functions ──────────────────────────────────────────────

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# ─── Check arguments ────────────────────────────────────────

if [ $# -eq 0 ]; then
    error "Usage: $0 <backup_file.sql.gz>"
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
fi

# Verify backup integrity
if ! gunzip -t "$BACKUP_FILE" 2>/dev/null; then
    error "Backup file is corrupted"
fi

log "Backup file: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# ─── Confirmation ───────────────────────────────────────────

echo ""
warn "⚠️  This will REPLACE the current database!"
echo ""
read -p "Are you sure you want to restore? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    error "Restore cancelled"
fi

# ─── Pre-flight checks ──────────────────────────────────────

log "Checking PostgreSQL container..."

if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    error "PostgreSQL container is not running"
fi

# ─── Stop services ──────────────────────────────────────────

log "Stopping scraper services..."

docker-compose stop scraper dashboard || warn "Failed to stop services (continuing anyway)"

sleep 2

# ─── Drop existing database ─────────────────────────────────

log "Dropping existing database..."

docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" postgres || error "Failed to drop database"

log "Creating fresh database..."

docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;" postgres || error "Failed to create database"

# ─── Restore backup ─────────────────────────────────────────

log "Restoring backup..."

if gunzip -c "$BACKUP_FILE" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
    log "✓ Backup restored successfully"
else
    error "Restore failed"
fi

# ─── Verify restore ─────────────────────────────────────────

log "Verifying restore..."

TABLES_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')

if [ "$TABLES_COUNT" -gt 0 ]; then
    log "✓ Database has $TABLES_COUNT tables"
else
    error "Database seems empty"
fi

# ─── Restart services ───────────────────────────────────────

log "Restarting scraper services..."

docker-compose up -d scraper dashboard

sleep 5

# Test API health
if curl -s http://localhost:8000/health | grep -q '"status":"ok"'; then
    log "✓ API is healthy"
else
    warn "API health check failed"
fi

# ─── Summary ────────────────────────────────────────────────

log "Restore completed successfully!"
log "  Backup file: $BACKUP_FILE"
log "  Tables restored: $TABLES_COUNT"
log "  Services: restarted"

exit 0
