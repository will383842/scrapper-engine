"""Proxy rotation manager with circuit breaker pattern."""

import json
import logging
import os
import random
import time

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy rotation with weighted selection and circuit breaker."""

    def __init__(self):
        self.provider = os.getenv("PROXY_PROVIDER", "oxylabs")
        self.user = os.getenv("PROXY_USER", "")
        self.password = os.getenv("PROXY_PASS", "")

        config_path = os.getenv(
            "PROXY_CONFIG",
            os.path.join(os.path.dirname(__file__), "../../config/proxy_config.json"),
        )
        with open(config_path, "r") as f:
            self.config = json.load(f)

        provider_config = self.config["providers"].get(self.provider, {})
        self.endpoint = provider_config.get("endpoint", "")
        self.pool_size = provider_config.get("pool_size", 20)

        # Circuit breaker state per proxy
        self._failures: dict[str, int] = {}
        self._cooldown_until: dict[str, float] = {}

        rotation = self.config.get("rotation", {})
        self.max_failures = rotation.get("max_consecutive_failures", 5)
        self.cooldown_steps = rotation.get("cooldown_minutes", [5, 10, 20, 30])

    def get_proxy(self) -> str | None:
        """Get next available proxy URL."""
        if not self.endpoint or not self.user:
            return None

        # Generate session-based proxy URL
        session_id = random.randint(1, self.pool_size)
        proxy_url = f"http://{self.user}-session-{session_id}:{self.password}@{self.endpoint}"

        # Check circuit breaker
        if self._is_in_cooldown(proxy_url):
            # Try another session
            for _ in range(5):
                session_id = random.randint(1, self.pool_size)
                proxy_url = f"http://{self.user}-session-{session_id}:{self.password}@{self.endpoint}"
                if not self._is_in_cooldown(proxy_url):
                    break

        return proxy_url

    def report_failure(self, proxy_url: str):
        """Report a proxy failure, activate circuit breaker if needed."""
        self._failures[proxy_url] = self._failures.get(proxy_url, 0) + 1
        failures = self._failures[proxy_url]

        if failures >= self.max_failures:
            # Calculate cooldown duration
            cooldown_index = min(
                failures // self.max_failures - 1,
                len(self.cooldown_steps) - 1,
            )
            cooldown_minutes = self.cooldown_steps[cooldown_index]
            self._cooldown_until[proxy_url] = time.time() + (cooldown_minutes * 60)
            logger.warning(
                f"Proxy {proxy_url[:50]}... in cooldown for {cooldown_minutes}min "
                f"({failures} failures)"
            )

    def report_success(self, proxy_url: str):
        """Report a successful request, reset failure count."""
        self._failures[proxy_url] = 0

    def _is_in_cooldown(self, proxy_url: str) -> bool:
        """Check if proxy is in cooldown period."""
        until = self._cooldown_until.get(proxy_url, 0)
        if until > time.time():
            return True
        # Cooldown expired
        if proxy_url in self._cooldown_until:
            del self._cooldown_until[proxy_url]
        return False
