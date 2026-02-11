"""Tests for the proxy rotation manager with circuit breaker."""

import json
import os
import time

import pytest
from unittest.mock import patch, mock_open, MagicMock


# Minimal valid proxy config for tests
MOCK_PROXY_CONFIG = {
    "providers": {
        "oxylabs": {
            "endpoint": "pr.oxylabs.io:7777",
            "auth_type": "user_pass",
            "pool_size": 20,
            "type": "datacenter",
        }
    },
    "rotation": {
        "max_consecutive_failures": 5,
        "cooldown_minutes": [5, 10, 20, 30],
    },
}


def _make_proxy_manager(**env_overrides):
    """Create a ProxyManager with mocked config file and env vars."""
    env = {
        "PROXY_PROVIDER": "oxylabs",
        "PROXY_USER": "testuser",
        "PROXY_PASS": "testpass",
        "PROXY_CONFIG": "/fake/proxy_config.json",
    }
    env.update(env_overrides)

    config_json = json.dumps(MOCK_PROXY_CONFIG)
    with patch.dict(os.environ, env):
        with patch("builtins.open", mock_open(read_data=config_json)):
            from scraper.utils.proxy_manager import ProxyManager
            return ProxyManager()


class TestGetProxy:
    """Tests for ProxyManager.get_proxy()."""

    def test_get_proxy_returns_url(self):
        """With valid config, get_proxy should return a proxy URL."""
        mgr = _make_proxy_manager()
        proxy = mgr.get_proxy()

        assert proxy is not None
        assert proxy.startswith("http://")
        assert "testuser" in proxy
        assert "testpass" in proxy
        assert "pr.oxylabs.io:7777" in proxy

    def test_get_proxy_no_endpoint_returns_none(self):
        """If the provider has no endpoint, get_proxy should return None."""
        config_no_endpoint = {
            "providers": {
                "oxylabs": {
                    "endpoint": "",
                    "pool_size": 20,
                }
            },
            "rotation": {
                "max_consecutive_failures": 5,
                "cooldown_minutes": [5, 10, 20, 30],
            },
        }
        config_json = json.dumps(config_no_endpoint)
        env = {
            "PROXY_PROVIDER": "oxylabs",
            "PROXY_USER": "testuser",
            "PROXY_PASS": "testpass",
            "PROXY_CONFIG": "/fake/proxy_config.json",
        }
        with patch.dict(os.environ, env):
            with patch("builtins.open", mock_open(read_data=config_json)):
                from scraper.utils.proxy_manager import ProxyManager
                mgr = ProxyManager()

        assert mgr.get_proxy() is None

    def test_get_proxy_no_user_returns_none(self):
        """If PROXY_USER is empty, get_proxy should return None."""
        mgr = _make_proxy_manager(PROXY_USER="")
        assert mgr.get_proxy() is None


class TestCircuitBreaker:
    """Tests for the circuit breaker pattern in ProxyManager."""

    def test_circuit_breaker_cooldown(self):
        """After max_consecutive_failures, the proxy should enter cooldown."""
        mgr = _make_proxy_manager()
        proxy_url = "http://testuser-session-1:testpass@pr.oxylabs.io:7777"

        # Report failures up to the threshold
        for _ in range(mgr.max_failures):
            mgr.report_failure(proxy_url)

        # The proxy should now be in cooldown
        assert mgr._is_in_cooldown(proxy_url) is True

    def test_report_success_resets_failures(self):
        """report_success should reset the failure counter."""
        mgr = _make_proxy_manager()
        proxy_url = "http://testuser-session-1:testpass@pr.oxylabs.io:7777"

        # Accumulate some failures (but not enough to trigger cooldown)
        for _ in range(mgr.max_failures - 1):
            mgr.report_failure(proxy_url)
        assert mgr._failures[proxy_url] == mgr.max_failures - 1

        # Success resets the counter
        mgr.report_success(proxy_url)
        assert mgr._failures[proxy_url] == 0
        assert mgr._is_in_cooldown(proxy_url) is False

    def test_all_proxies_cooldown_returns_none(self):
        """When all proxy sessions are in cooldown, get_proxy returns None."""
        mgr = _make_proxy_manager()

        # Put every possible session in cooldown
        for session_id in range(1, mgr.pool_size + 1):
            proxy_url = f"http://testuser-session-{session_id}:testpass@pr.oxylabs.io:7777"
            mgr._cooldown_until[proxy_url] = time.time() + 3600  # far future

        # Mock random to always pick session IDs that are in cooldown
        with patch("scraper.utils.proxy_manager.random.randint") as mock_rand:
            # Return a fixed value within the pool so every attempt hits cooldown
            mock_rand.return_value = 1
            result = mgr.get_proxy()
            assert result is None

    def test_cooldown_expires(self):
        """A proxy should exit cooldown after the cooldown period expires."""
        mgr = _make_proxy_manager()
        proxy_url = "http://testuser-session-1:testpass@pr.oxylabs.io:7777"

        # Set cooldown to the past
        mgr._cooldown_until[proxy_url] = time.time() - 1

        assert mgr._is_in_cooldown(proxy_url) is False
        # The expired entry should be cleaned up
        assert proxy_url not in mgr._cooldown_until
