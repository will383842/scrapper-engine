"""Tests for the MailWizz API client."""

import os

import pytest
from unittest.mock import patch, MagicMock


class TestGetClient:
    """Tests for the get_client() factory function."""

    def setup_method(self):
        """Clear the module-level client cache before each test."""
        import scraper.integrations.mailwizz_client as mw_module
        mw_module._clients.clear()

    def test_get_client_sos_expat(self):
        """get_client('sos-expat') should return a configured MailWizzClient."""
        env = {
            "MAILWIZZ_SOS_EXPAT_API_URL": "https://mailwizz.sos-expat.test/api",
            "MAILWIZZ_SOS_EXPAT_API_KEY": "test-key-123",
        }
        with patch.dict(os.environ, env):
            from scraper.integrations.mailwizz_client import get_client

            client = get_client("sos-expat")
            assert client.api_url == "https://mailwizz.sos-expat.test/api"
            assert client.api_key == "test-key-123"

    def test_get_client_unknown_platform_raises(self):
        """get_client with an unknown platform should raise ValueError."""
        from scraper.integrations.mailwizz_client import get_client

        with pytest.raises(ValueError, match="Unknown platform"):
            get_client("some-random-platform")

    def test_get_client_missing_env_raises(self):
        """get_client should raise if env vars for the platform are not set."""
        env = {
            "MAILWIZZ_SOS_EXPAT_API_URL": "",
            "MAILWIZZ_SOS_EXPAT_API_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            from scraper.integrations.mailwizz_client import get_client

            with pytest.raises(ValueError, match="not configured"):
                get_client("sos-expat")


class TestAddSubscriber:
    """Tests for MailWizzClient.add_subscriber()."""

    def _make_client(self):
        from scraper.integrations.mailwizz_client import MailWizzClient

        # Use a mock httpx.Client under the hood
        client = MailWizzClient(
            api_url="https://mailwizz.test/api",
            api_key="test-key",
        )
        return client

    def test_add_subscriber_success(self):
        """A 201 response should return success with the subscriber UID."""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "record": {
                    "subscriber_uid": "abc123",
                    "email": "new@example.com",
                }
            },
        }
        client.client = MagicMock()
        client.client.post.return_value = mock_response

        result = client.add_subscriber(
            list_id=1,
            data={"EMAIL": "new@example.com", "FNAME": "Jane"},
            tags=["avocat", "FR"],
        )

        assert result["success"] is True
        assert result["subscriber_uid"] == "abc123"
        # Verify the tags were joined and sent
        call_kwargs = client.client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["tags"] == "avocat,FR"

    def test_add_subscriber_failure(self):
        """A 400 response should return success=False with the error."""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Email already exists in the list.",
        }
        client.client = MagicMock()
        client.client.post.return_value = mock_response

        result = client.add_subscriber(list_id=1, data={"EMAIL": "dupe@example.com"})
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_add_subscriber_exception(self):
        """If httpx raises an exception, the client should catch it and return an error."""
        client = self._make_client()

        client.client = MagicMock()
        client.client.post.side_effect = ConnectionError("Network unreachable")

        result = client.add_subscriber(list_id=1, data={"EMAIL": "fail@example.com"})
        assert result["success"] is False
        assert "Network unreachable" in result["error"]
