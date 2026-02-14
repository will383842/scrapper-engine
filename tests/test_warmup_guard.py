"""Tests for warmup_guard integration module."""

import os
from unittest.mock import patch, MagicMock

import httpx
import pytest


class TestGetDailyQuotaRemaining:
    """Test warmup_guard.get_daily_quota_remaining()."""

    def _import_fresh(self):
        """Import with a fresh module to pick up env vars."""
        import importlib
        import scraper.integrations.warmup_guard as wg
        importlib.reload(wg)
        return wg.get_daily_quota_remaining

    @patch.dict(os.environ, {"WARMUP_CHECK_ENABLED": "false"}, clear=False)
    def test_disabled_returns_none(self):
        """When warmup check is disabled, returns None (no limit)."""
        fn = self._import_fresh()
        result = fn()
        assert result is None

    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "",
    }, clear=False)
    def test_no_api_url_returns_none(self):
        """When API URL is not configured, returns None."""
        fn = self._import_fresh()
        result = fn()
        assert result is None

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "test-key",
    }, clear=False)
    def test_single_active_plan_returns_quota(self, mock_get):
        """Single active warmup plan -> returns 80% of daily quota."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "phase": "week_2",
                "current_daily_quota": 500,
                "paused": False,
                "bounce_rate_7d": 1.2,
                "spam_rate_7d": 0.1,
            }
        ]
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        result = fn()

        assert result == 400  # 500 * 0.8
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "warmup/plans" in call_args[0][0]
        assert call_args[1]["headers"]["X-API-Key"] == "test-key"

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_multiple_plans_sums_quotas(self, mock_get):
        """Multiple active plans -> sum of daily quotas * 0.8."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"phase": "week_1", "current_daily_quota": 200, "paused": False},
            {"phase": "week_3", "current_daily_quota": 800, "paused": False},
        ]
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        result = fn()

        assert result == 800  # (200 + 800) * 0.8

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_paused_plans_are_skipped(self, mock_get):
        """Paused plans should not count toward quota."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"phase": "week_2", "current_daily_quota": 500, "paused": True},
            {"phase": "week_4", "current_daily_quota": 1000, "paused": False},
        ]
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        result = fn()

        assert result == 800  # Only 1000 * 0.8 (paused plan excluded)

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_done_plans_are_skipped(self, mock_get):
        """Plans with phase='done' should not count."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"phase": "done", "current_daily_quota": 5000, "paused": False},
        ]
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        result = fn()

        # All plans are done -> no active warmup -> no limit
        assert result is None

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_all_paused_returns_none(self, mock_get):
        """All plans paused -> no active warmup -> no limit."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"phase": "week_2", "current_daily_quota": 500, "paused": True},
        ]
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        result = fn()

        assert result is None

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_empty_plans_returns_none(self, mock_get):
        """Empty plans list -> no warmup restriction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        result = fn()

        assert result is None

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_api_error_returns_zero_failsafe(self, mock_get):
        """Non-200 response -> fail-safe: return 0 (pause sending)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        result = fn()

        assert result == 0

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_timeout_returns_zero_failsafe(self, mock_get):
        """Timeout -> fail-safe: return 0 (pause sending)."""
        mock_get.side_effect = httpx.TimeoutException("Connection timed out")

        fn = self._import_fresh()
        result = fn()

        assert result == 0

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_connection_error_returns_zero_failsafe(self, mock_get):
        """Connection error -> fail-safe: return 0."""
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        fn = self._import_fresh()
        result = fn()

        assert result == 0

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_unexpected_exception_returns_zero_failsafe(self, mock_get):
        """Unexpected exception -> fail-safe: return 0."""
        mock_get.side_effect = ValueError("Unexpected")

        fn = self._import_fresh()
        result = fn()

        assert result == 0

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000/",
        "EMAIL_ENGINE_API_KEY": "my-key",
    }, clear=False)
    def test_trailing_slash_stripped_from_url(self, mock_get):
        """Trailing slash on API URL should be stripped."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        fn()

        url_called = mock_get.call_args[0][0]
        assert "//" not in url_called.split("://")[1]  # No double slash in path
        assert url_called == "http://engine:8000/api/v1/warmup/plans"

    @patch("httpx.get")
    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
    }, clear=False)
    def test_single_plan_object_not_list(self, mock_get):
        """API returns a single plan object instead of a list -> should still work."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phase": "week_3",
            "current_daily_quota": 1000,
            "paused": False,
        }
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        result = fn()

        assert result == 800  # 1000 * 0.8

    @patch.dict(os.environ, {
        "WARMUP_CHECK_ENABLED": "true",
        "EMAIL_ENGINE_API_URL": "http://engine:8000",
        "EMAIL_ENGINE_API_KEY": "",
        "WARMUP_QUOTA_USAGE_RATIO": "0.5",
    }, clear=False)
    @patch("httpx.get")
    def test_custom_quota_ratio(self, mock_get):
        """Custom WARMUP_QUOTA_USAGE_RATIO env var is respected."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"phase": "week_1", "current_daily_quota": 1000, "paused": False},
        ]
        mock_get.return_value = mock_response

        fn = self._import_fresh()
        result = fn()

        assert result == 500  # 1000 * 0.5
