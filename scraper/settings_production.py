"""
Scrapy settings for scraper-pro (PRODUCTION)
==============================================

Optimized for:
- Hetzner CPX31 (4 vCPU, 8GB RAM)
- URLs only mode (NO proxies, NO Google)
- Maximum deduplication
- High concurrency
"""

import os

BOT_NAME = "scraper-pro"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

# ────────────────────────────────────────────────────────────
# SCRAPING MODE
# ────────────────────────────────────────────────────────────

SCRAPING_MODE = os.getenv("SCRAPING_MODE", "urls_only")

# ────────────────────────────────────────────────────────────
# ROBOTS.TXT
# ────────────────────────────────────────────────────────────
# IMPORTANT: Must be False for Google Search/Maps to work
# In "urls_only" mode, this setting has no impact (no Google scraping)

ROBOTSTXT_OBEY = False

# ────────────────────────────────────────────────────────────
# CONCURRENCY (PRODUCTION OPTIMIZED)
# ────────────────────────────────────────────────────────────

if SCRAPING_MODE == "urls_only":
    # URLs only: high concurrency, no proxies
    CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", "16"))
    CONCURRENT_REQUESTS_PER_DOMAIN = int(os.getenv("CONCURRENT_REQUESTS_PER_DOMAIN", "4"))
    DOWNLOAD_DELAY = float(os.getenv("DOWNLOAD_DELAY", "1.0"))
else:
    # Full mode: lower concurrency (proxies + Google)
    CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", "8"))
    CONCURRENT_REQUESTS_PER_DOMAIN = int(os.getenv("CONCURRENT_REQUESTS_PER_DOMAIN", "2"))
    DOWNLOAD_DELAY = float(os.getenv("DOWNLOAD_DELAY", "2.0"))

RANDOMIZE_DOWNLOAD_DELAY = True

# ────────────────────────────────────────────────────────────
# COOKIES & TRACKING
# ────────────────────────────────────────────────────────────

COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False

# ────────────────────────────────────────────────────────────
# MIDDLEWARES
# ────────────────────────────────────────────────────────────

DOWNLOADER_MIDDLEWARES = {
    "scraper.utils.middlewares.RandomUserAgentMiddleware": 400,
    "scraper.utils.middlewares.ProxyMiddleware": 410,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": None,
}

# ────────────────────────────────────────────────────────────
# PIPELINES (WITH ULTRA-PRO DEDUPLICATION)
# ────────────────────────────────────────────────────────────

ITEM_PIPELINES = {
    "scraper.utils.pipelines.UltraProDeduplicationPipeline": 50,  # NEW: Multi-layer dedup
    "scraper.utils.pipelines.ValidationPipeline": 200,
    "scraper.utils.pipelines.PostgresPipeline": 300,
    "scraper.utils.pipelines.ArticlePipeline": 350,
    "scraper.utils.pipelines.ProgressTrackingPipeline": 400,
}

# ────────────────────────────────────────────────────────────
# AUTO-THROTTLE
# ────────────────────────────────────────────────────────────

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0 if SCRAPING_MODE == "urls_only" else 2.0
AUTOTHROTTLE_MAX_DELAY = 20.0 if SCRAPING_MODE == "urls_only" else 30.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0 if SCRAPING_MODE == "urls_only" else 2.0
AUTOTHROTTLE_DEBUG = False

# ────────────────────────────────────────────────────────────
# SMART THROTTLE (INTELLIGENT AUTO-ADJUSTMENT)
# ────────────────────────────────────────────────────────────

SMART_THROTTLE_MIN_DELAY = float(os.getenv("SMART_THROTTLE_MIN_DELAY", "0.5"))
SMART_THROTTLE_MAX_DELAY = float(os.getenv("SMART_THROTTLE_MAX_DELAY", "30.0"))

EXTENSIONS = {
    'scraper.utils.smart_throttle.SmartThrottleExtension': 500,
}

# ────────────────────────────────────────────────────────────
# RETRY
# ────────────────────────────────────────────────────────────

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# ────────────────────────────────────────────────────────────
# TIMEOUTS
# ────────────────────────────────────────────────────────────

DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "30"))

# ────────────────────────────────────────────────────────────
# LOGGING
# ────────────────────────────────────────────────────────────

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# ────────────────────────────────────────────────────────────
# CACHE (DISABLED IN PRODUCTION)
# ────────────────────────────────────────────────────────────

HTTPCACHE_ENABLED = False

# ────────────────────────────────────────────────────────────
# DEDUPLICATION (ULTRA-PRO SETTINGS)
# ────────────────────────────────────────────────────────────

DEDUP_URL_TTL_DAYS = int(os.getenv("DEDUP_URL_TTL_DAYS", "30"))
DEDUP_EMAIL_GLOBAL = os.getenv("DEDUP_EMAIL_GLOBAL", "true").lower() == "true"
DEDUP_CONTENT_HASH_ENABLED = os.getenv("DEDUP_CONTENT_HASH_ENABLED", "true").lower() == "true"
DEDUP_URL_NORMALIZE = os.getenv("DEDUP_URL_NORMALIZE", "true").lower() == "true"

# ────────────────────────────────────────────────────────────
# FEED EXPORTS (OPTIONAL)
# ────────────────────────────────────────────────────────────

FEED_EXPORT_ENCODING = "utf-8"
FEED_EXPORT_INDENT = 2

# ────────────────────────────────────────────────────────────
# MEMORY & PERFORMANCE
# ────────────────────────────────────────────────────────────

# Close spider if idle for 60 seconds
CLOSESPIDER_TIMEOUT = 60

# Close spider if too many errors (protection)
CLOSESPIDER_ERRORCOUNT = 100

# Item pipeline memory limit (drop items if queue too large)
CONCURRENT_ITEMS = 100

# ────────────────────────────────────────────────────────────
# DNS & CONNECTION POOLING
# ────────────────────────────────────────────────────────────

DNS_TIMEOUT = 10
DOWNLOAD_MAXSIZE = 10485760  # 10 MB
DOWNLOAD_WARNSIZE = 5242880   # 5 MB

# Connection pool size
CONCURRENT_REQUESTS_PER_IP = 4

# ────────────────────────────────────────────────────────────
# COMPRESSION
# ────────────────────────────────────────────────────────────

COMPRESSION_ENABLED = True

# ────────────────────────────────────────────────────────────
# STATS
# ────────────────────────────────────────────────────────────

STATS_CLASS = "scrapy.statscollectors.MemoryStatsCollector"
STATS_DUMP = True
