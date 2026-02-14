#!/bin/bash
# ============================================================
# PostgreSQL Backup Script for Scraper-Pro
# ============================================================
# Usage: ./scripts/backup-postgres.sh
# Schedule: crontab -e → 0 3 * * * /path/to/backup-postgres.sh
# ============================================================

set -e

# ─── Configuration ──────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/var/backups/scraper-pro}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
POSTGRES_CONTAINER="scraper-postgres"
POSTGRES_USER="scraper_admin"
POSTGRES_DB="scraper_db"
DATE=$(date +%Y-%m-%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/scraper_db_${DATE}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# ─── Colors ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ─── Functions ──────────────────────────────────────────────

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# ─── Pre-flight checks ──────────────────────────────────────

log "Starting PostgreSQL backup..."

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR" || error "Failed to create backup directory"
fi

# Check if PostgreSQL container is running
if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    error "PostgreSQL container is not running"
fi

# Check available disk space (need at least 1GB)
AVAILABLE_SPACE=$(df -BG "$BACKUP_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 1 ]; then
    error "Not enough disk space (${AVAILABLE_SPACE}GB available, need at least 1GB)"
fi

# ─── Create backup ──────────────────────────────────────────

log "Creating backup: $BACKUP_FILE"

# Dump database and compress
if docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "✓ Backup created successfully ($BACKUP_SIZE)"
else
    error "pg_dump failed"
fi

# Verify backup integrity
if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
    log "✓ Backup integrity verified"
else
    warn "Backup file may be corrupted"
fi

# ─── Cleanup old backups ────────────────────────────────────

log "Cleaning up backups older than $RETENTION_DAYS days..."

DELETED_COUNT=0
while IFS= read -r old_backup; do
    rm -f "$old_backup"
    DELETED_COUNT=$((DELETED_COUNT + 1))
    log "  Deleted: $(basename "$old_backup")"
done < <(find "$BACKUP_DIR" -name "scraper_db_*.sql.gz" -type f -mtime +$RETENTION_DAYS)

if [ "$DELETED_COUNT" -eq 0 ]; then
    log "No old backups to delete"
else
    log "✓ Deleted $DELETED_COUNT old backup(s)"
fi

# ─── Summary ────────────────────────────────────────────────

BACKUP_COUNT=$(find "$BACKUP_DIR" -name "scraper_db_*.sql.gz" -type f | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

log "Backup completed successfully!"
log "  Latest backup: $BACKUP_FILE ($BACKUP_SIZE)"
log "  Total backups: $BACKUP_COUNT"
log "  Total size: $TOTAL_SIZE"
log "  Retention: $RETENTION_DAYS days"

# ─── Optional: Upload to S3/GCS ─────────────────────────────

if [ -n "${AWS_S3_BUCKET}" ]; then
    log "Uploading backup to S3: s3://${AWS_S3_BUCKET}/scraper-pro/"
    if aws s3 cp "$BACKUP_FILE" "s3://${AWS_S3_BUCKET}/scraper-pro/" --storage-class STANDARD_IA; then
        log "✓ Backup uploaded to S3"
    else
        warn "Failed to upload backup to S3"
    fi
fi

# ─── Send notification (optionnel) ──────────────────────────

if [ -n "${SLACK_WEBHOOK_URL}" ]; then
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Scraper-Pro backup completed\\n• File: \`$(basename "$BACKUP_FILE")\`\\n• Size: $BACKUP_SIZE\\n• Backups: $BACKUP_COUNT\"}" \
        > /dev/null 2>&1
fi

exit 0
