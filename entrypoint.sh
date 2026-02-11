#!/bin/bash
set -e

# Export environment variables for cron jobs
# Cron runs in a clean shell without Docker env vars
printenv | grep -E '^(POSTGRES_|REDIS_|MAILWIZZ_|PROXY_|API_HMAC_SECRET|LOG_LEVEL|DASHBOARD_)' >> /etc/environment

echo "Starting cron daemon..."
cron

echo "Starting uvicorn API server..."
exec uvicorn scraper.api.main:app --host 0.0.0.0 --port 8000
