"""Scrapy middlewares for user-agent rotation and proxy injection."""

import random
import logging

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


class RandomUserAgentMiddleware:
    """Rotate user agents on every request."""

    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(USER_AGENTS)


class ProxyMiddleware:
    """Inject proxy from the proxy manager."""

    def __init__(self):
        self._proxy_manager = None

    def _get_proxy_manager(self):
        if self._proxy_manager is None:
            from scraper.utils.proxy_manager import ProxyManager
            self._proxy_manager = ProxyManager()
        return self._proxy_manager

    def process_request(self, request, spider):
        pm = self._get_proxy_manager()
        proxy = pm.get_proxy()
        if proxy:
            request.meta["proxy"] = proxy
            logger.debug(f"Using proxy: {proxy} for {request.url}")

    def process_exception(self, request, exception, spider):
        proxy = request.meta.get("proxy")
        if proxy:
            pm = self._get_proxy_manager()
            pm.report_failure(proxy)
            logger.warning(f"Proxy failed: {proxy} - {exception}")
