"""Prometheus metrics for Scraper-Pro API."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import logging

logger = logging.getLogger(__name__)

# ─── HTTP Metrics ────────────────────────────────────────

http_requests_total = Counter(
    'scraper_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'scraper_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# ─── Jobs Metrics ────────────────────────────────────────

jobs_total = Counter(
    'scraper_jobs_total',
    'Total scraping jobs created',
    ['source_type']
)

jobs_running = Gauge(
    'scraper_jobs_running',
    'Currently running jobs',
    ['source_type']
)

jobs_completed_total = Counter(
    'scraper_jobs_completed_total',
    'Total completed jobs',
    ['source_type', 'status']  # status: completed or failed
)

jobs_failed_total = Counter(
    'scraper_jobs_failed_total',
    'Total failed jobs',
    ['source_type']
)

# ─── Contacts Metrics ────────────────────────────────────

contacts_scraped_total = Counter(
    'scraper_contacts_scraped_total',
    'Total contacts scraped',
    ['source_type']
)

contacts_validated_total = Counter(
    'scraper_contacts_validated_total',
    'Total contacts validated',
    ['category', 'platform']
)

contacts_rejected_total = Counter(
    'scraper_contacts_rejected_total',
    'Total contacts rejected',
    ['reason']  # invalid_email, duplicate, blacklisted_domain
)

# ─── MailWizz Sync Metrics ───────────────────────────────

mailwizz_sync_total = Counter(
    'scraper_mailwizz_sync_total',
    'Total MailWizz sync attempts',
    ['platform']
)

mailwizz_sync_success_total = Counter(
    'scraper_mailwizz_sync_success_total',
    'Total successful MailWizz syncs',
    ['platform', 'list_id']
)

mailwizz_sync_failed_total = Counter(
    'scraper_mailwizz_sync_failed_total',
    'Total failed MailWizz syncs',
    ['platform', 'error_type']
)

contacts_bounced_total = Counter(
    'scraper_contacts_bounced_total',
    'Total bounced contacts',
    ['platform']
)

contacts_sent_total = Counter(
    'scraper_contacts_sent_total',
    'Total contacts sent to MailWizz',
    ['platform']
)

# ─── Proxy Metrics ───────────────────────────────────────

proxy_requests_total = Counter(
    'scraper_proxy_requests_total',
    'Total proxy requests',
    ['proxy_provider', 'proxy_type']
)

proxy_failures_total = Counter(
    'scraper_proxy_failures_total',
    'Total proxy failures',
    ['proxy_provider', 'error_type']
)

proxy_response_time_seconds = Histogram(
    'scraper_proxy_response_time_seconds',
    'Proxy response time in seconds',
    ['proxy_provider']
)

# ─── WHOIS Metrics ───────────────────────────────────────

whois_lookups_total = Counter(
    'scraper_whois_lookups_total',
    'Total WHOIS lookups',
    ['status']  # success, failed
)

whois_cache_hits_total = Counter(
    'scraper_whois_cache_hits_total',
    'Total WHOIS cache hits'
)

# ─── Metrics Endpoint ────────────────────────────────────

def metrics_endpoint() -> Response:
    """Generate Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
