"""Tests for checkpoint and URL fingerprint services."""

import json

import pytest
from unittest.mock import patch, MagicMock, call

from scraper.utils.checkpoint import (
    _hash_url,
    is_url_seen,
    load_checkpoint,
    mark_url_seen,
    save_checkpoint,
    update_progress,
    get_completed_urls_for_job,
)


class TestHashUrl:
    """Tests for URL normalization and hashing."""

    def test_same_url_same_hash(self):
        """Identical URLs should produce the same hash."""
        assert _hash_url("https://example.com/page") == _hash_url("https://example.com/page")

    def test_trailing_slash_normalized(self):
        """Trailing slashes should be stripped before hashing."""
        assert _hash_url("https://example.com/page/") == _hash_url("https://example.com/page")

    def test_case_insensitive_host(self):
        """Host portion should be case-insensitive."""
        assert _hash_url("https://EXAMPLE.COM/page") == _hash_url("https://example.com/page")

    def test_different_paths_different_hash(self):
        """Different paths should produce different hashes."""
        assert _hash_url("https://example.com/a") != _hash_url("https://example.com/b")

    def test_query_string_preserved(self):
        """Query strings should be included in the hash."""
        assert _hash_url("https://example.com?q=1") != _hash_url("https://example.com?q=2")

    def test_returns_hex_string(self):
        """Hash should be a 64-char hex string (SHA-256)."""
        h = _hash_url("https://example.com")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestSaveCheckpoint:
    """Tests for save_checkpoint."""

    def test_saves_checkpoint_data(self):
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            save_checkpoint(42, {"urls_completed": 5, "contacts_found": 12})

        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["job_id"] == 42
        data = json.loads(params["data"])
        assert data["urls_completed"] == 5
        assert data["contacts_found"] == 12

    def test_handles_db_error_gracefully(self):
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(side_effect=Exception("DB down"))

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            # Should not raise
            save_checkpoint(1, {"test": True})


class TestLoadCheckpoint:
    """Tests for load_checkpoint."""

    def test_loads_json_string(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar.return_value = '{"urls_completed": 10}'
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            result = load_checkpoint(42)

        assert result == {"urls_completed": 10}

    def test_loads_dict_directly(self):
        """When PostgreSQL returns JSONB as a dict, it should work without json.loads."""
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar.return_value = {"urls_completed": 10}
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            result = load_checkpoint(42)

        assert result == {"urls_completed": 10}

    def test_returns_empty_dict_on_no_data(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar.return_value = None
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            result = load_checkpoint(42)

        assert result == {}

    def test_returns_empty_dict_on_error(self):
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(side_effect=Exception("DB error"))

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            result = load_checkpoint(42)

        assert result == {}


class TestUpdateProgress:
    """Tests for update_progress."""

    def test_updates_progress_fields(self):
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            update_progress(42, 65.5, pages=3, contacts=25)

        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["progress"] == 65.5
        assert params["pages"] == 3
        assert params["contacts"] == 25
        assert params["job_id"] == 42

    def test_caps_progress_at_100(self):
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            update_progress(42, 150.0)

        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["progress"] == 100.0


class TestIsUrlSeen:
    """Tests for is_url_seen."""

    def test_returns_true_when_found(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar.return_value = 1
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            assert is_url_seen("https://example.com") is True

    def test_returns_false_when_not_found(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar.return_value = None
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            assert is_url_seen("https://example.com") is False

    def test_returns_false_on_error(self):
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(side_effect=Exception("DB error"))

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            assert is_url_seen("https://example.com") is False


class TestMarkUrlSeen:
    """Tests for mark_url_seen."""

    def test_inserts_url_fingerprint(self):
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            mark_url_seen("https://example.com/page", spider_name="google_search")

        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["url"] == "https://example.com/page"
        assert params["domain"] == "example.com"
        assert params["spider"] == "google_search"
        assert len(params["hash"]) == 64


class TestGetCompletedUrlsForJob:
    """Tests for get_completed_urls_for_job."""

    def test_returns_set_of_urls(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            "https://site1.com",
            "https://site2.com",
        ]
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            result = get_completed_urls_for_job(42)

        assert result == {"https://site1.com", "https://site2.com"}

    def test_returns_empty_set_on_error(self):
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(side_effect=Exception("DB error"))

        with patch("scraper.utils.checkpoint.get_db_session", return_value=mock_cm):
            result = get_completed_urls_for_job(42)

        assert result == set()
