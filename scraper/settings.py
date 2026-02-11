"""Scrapy settings for scraper-pro."""

import os

BOT_NAME = "scraper-pro"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

# Respect robots.txt by default
ROBOTSTXT_OBEY = True

# Concurrent requests (conservative for proxy usage)
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Download delay between requests (seconds)
DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = True

# Disable cookies to avoid tracking
COOKIES_ENABLED = False

# User agent rotation
USER_AGENT = None  # Handled by middleware
DOWNLOADER_MIDDLEWARES = {
    "scraper.utils.middlewares.RandomUserAgentMiddleware": 400,
    "scraper.utils.middlewares.ProxyMiddleware": 410,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": None,
}

ITEM_PIPELINES = {
    "scraper.utils.pipelines.DeduplicationPipeline": 100,
    "scraper.utils.pipelines.ValidationPipeline": 200,
    "scraper.utils.pipelines.PostgresPipeline": 300,
}

# Auto-throttle
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 30
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Retry
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

# Timeouts
DOWNLOAD_TIMEOUT = 30

# Cache (avoid re-downloading during development)
HTTPCACHE_ENABLED = False
