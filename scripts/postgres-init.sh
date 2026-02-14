#!/bin/bash
# ========================================
# Script d'initialisation PostgreSQL
# ========================================
# Créer 2 bases de données distinctes :
# 1. scraper_db (Scraper-Pro)
# 2. backlink_db (Backlink Engine)
# ========================================

set -e
set -u

function create_database() {
    local database=$1
    echo "🗄️  Creating database '$database'..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        SELECT 'CREATE DATABASE $database'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
    echo "✅ Database '$database' created successfully"
}

# Main execution
echo "=========================================="
echo "📦 PostgreSQL Multi-Database Initialization"
echo "=========================================="

if [ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
    echo "🔍 Found multiple databases to create: $POSTGRES_MULTIPLE_DATABASES"

    # Split by comma
    IFS=',' read -ra DATABASES <<< "$POSTGRES_MULTIPLE_DATABASES"

    for db in "${DATABASES[@]}"; do
        # Trim whitespace
        db=$(echo "$db" | xargs)
        create_database "$db"
    done

    echo "=========================================="
    echo "✅ All databases created successfully!"
    echo "=========================================="
else
    echo "⚠️  No POSTGRES_MULTIPLE_DATABASES variable found"
    echo "    Skipping multi-database creation"
fi

# Create extensions for scraper_db
echo ""
echo "📦 Installing PostgreSQL extensions for scraper_db..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname=scraper_db <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
EOSQL
echo "✅ Extensions installed"

# Create extensions for backlink_db (si nécessaire)
echo ""
echo "📦 Installing PostgreSQL extensions for backlink_db..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname=backlink_db <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL
echo "✅ Extensions installed"

echo ""
echo "=========================================="
echo "🎉 PostgreSQL initialization complete!"
echo "=========================================="
echo ""
echo "📊 Databases created:"
echo "   1. scraper_db    → Scraper-Pro"
echo "   2. backlink_db   → Backlink Engine"
echo ""
echo "🔌 Connection strings:"
echo "   Scraper:  postgresql://$POSTGRES_USER:***@postgres:5432/scraper_db"
echo "   Backlink: postgresql://$POSTGRES_USER:***@postgres:5432/backlink_db"
echo "=========================================="
