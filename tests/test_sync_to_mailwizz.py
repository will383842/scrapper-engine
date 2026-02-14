"""Tests for sync_to_mailwizz cron job."""

import json
from unittest.mock import patch, MagicMock

import pytest

from scraper.jobs.sync_to_mailwizz import sync_contacts_to_mailwizz, BATCH_SIZE, MAX_RETRIES


def _make_validated_contact(id_: int, email: str, **overrides):
    """Build a fake validated_contacts row."""
    base = {
        "id": id_,
        "email": email,
        "name": "Test User",
        "phone": "+33612345678",
        "website": "https://example.com",
        "address": "1 Rue Test, Paris",
        "social_media": json.dumps({"linkedin": "https://linkedin.com/in/test"}),
        "category": "avocat",
        "platform": "sos-expat",
        "country": "FR",
        "tags": json.dumps(["avocat", "google_search", "FR"]),
        "email_valid": True,
        "phone_valid": True,
        "mailwizz_list_id": 10,
        "mailwizz_template": "avocat_intro",
        "status": "ready_for_mailwizz",
        "retry_count": 0,
        "last_error": None,
    }
    base.update(overrides)
    return base


class TestSyncContactsToMailwizz:
    """Test the sync_contacts_to_mailwizz function."""

    @patch("scraper.jobs.sync_to_mailwizz.get_client")
    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_successful_sync(self, mock_db, mock_quota, mock_get_client):
        """Happy path: contact synced successfully to MailWizz."""
        contact = _make_validated_contact(1, "avocat@law.com")
        mock_quota.return_value = None  # No warmup restriction

        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [contact]
        # begin_nested returns a savepoint mock
        savepoint = MagicMock()
        session.begin_nested.return_value = savepoint
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        client = MagicMock()
        client.add_subscriber.return_value = {
            "success": True,
            "subscriber_uid": "abc123",
        }
        mock_get_client.return_value = client

        stats = sync_contacts_to_mailwizz()

        assert stats["success"] == 1
        assert stats["failed"] == 0
        assert stats["retries"] == 0
        # Verify MailWizz was called with correct data
        client.add_subscriber.assert_called_once()
        call_kwargs = client.add_subscriber.call_args[1]
        assert call_kwargs["list_id"] == 10
        assert call_kwargs["data"]["EMAIL"] == "avocat@law.com"
        assert call_kwargs["data"]["CATEGORY"] == "avocat"
        # Savepoint committed
        savepoint.commit.assert_called_once()

    @patch("scraper.jobs.sync_to_mailwizz.get_client")
    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_mailwizz_api_failure_increments_retry(self, mock_db, mock_quota, mock_get_client):
        """MailWizz API failure -> retry_count incremented, stays ready_for_mailwizz."""
        contact = _make_validated_contact(2, "retry@law.com", retry_count=0)
        mock_quota.return_value = None

        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [contact]
        savepoint = MagicMock()
        session.begin_nested.return_value = savepoint
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        client = MagicMock()
        client.add_subscriber.return_value = {
            "success": False,
            "error": "MailWizz API 500",
        }
        mock_get_client.return_value = client

        stats = sync_contacts_to_mailwizz()

        assert stats["retries"] == 1
        assert stats["success"] == 0
        assert stats["failed"] == 0
        savepoint.commit.assert_called_once()

    @patch("scraper.jobs.sync_to_mailwizz.get_client")
    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_max_retries_marks_as_failed(self, mock_db, mock_quota, mock_get_client):
        """After MAX_RETRIES, contact is marked as 'failed'."""
        contact = _make_validated_contact(3, "dead@law.com", retry_count=MAX_RETRIES - 1)
        mock_quota.return_value = None

        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [contact]
        savepoint = MagicMock()
        session.begin_nested.return_value = savepoint
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        client = MagicMock()
        client.add_subscriber.return_value = {"success": False, "error": "Timeout"}
        mock_get_client.return_value = client

        stats = sync_contacts_to_mailwizz()

        assert stats["failed"] == 1
        assert stats["retries"] == 0

    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_warmup_quota_exhausted_skips_sync(self, mock_db, mock_quota):
        """When warmup quota is 0, sync is skipped entirely."""
        mock_quota.return_value = 0

        stats = sync_contacts_to_mailwizz()

        assert stats == {"success": 0, "failed": 0, "retries": 0, "held_warmup": 0}
        # DB should never be called
        mock_db.assert_not_called()

    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_warmup_quota_limits_batch(self, mock_db, mock_quota):
        """Warmup quota smaller than BATCH_SIZE -> effective_limit capped."""
        mock_quota.return_value = 25  # Less than BATCH_SIZE (100)

        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = []
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        stats = sync_contacts_to_mailwizz()

        # Check LIMIT parameter passed to SQL query
        first_call_params = session.execute.call_args_list[0][0][1]
        assert first_call_params["limit"] == 25

    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_warmup_disabled_uses_full_batch(self, mock_db, mock_quota):
        """When warmup is disabled (None), full BATCH_SIZE is used."""
        mock_quota.return_value = None

        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = []
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        stats = sync_contacts_to_mailwizz()

        first_call_params = session.execute.call_args_list[0][0][1]
        assert first_call_params["limit"] == BATCH_SIZE

    @patch("scraper.jobs.sync_to_mailwizz.get_client")
    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_exception_rolls_back_savepoint_continues_batch(
        self, mock_db, mock_quota, mock_get_client,
    ):
        """If one contact throws, savepoint rolls back but batch continues."""
        contacts = [
            _make_validated_contact(10, "ok@law.com"),
            _make_validated_contact(11, "crash@law.com"),
            _make_validated_contact(12, "also-ok@law.com"),
        ]
        mock_quota.return_value = None

        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = contacts

        savepoints = [MagicMock(), MagicMock(), MagicMock()]
        session.begin_nested.side_effect = savepoints
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        # 1st and 3rd succeed, 2nd throws exception
        client = MagicMock()
        client.add_subscriber.side_effect = [
            {"success": True, "subscriber_uid": "a1"},
            RuntimeError("Connection reset"),
            {"success": True, "subscriber_uid": "a3"},
        ]
        mock_get_client.return_value = client

        stats = sync_contacts_to_mailwizz()

        assert stats["success"] == 2
        assert stats["failed"] == 1
        # Savepoint 0 and 2 committed, savepoint 1 rolled back
        savepoints[0].commit.assert_called_once()
        savepoints[1].rollback.assert_called_once()
        savepoints[2].commit.assert_called_once()

    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_select_uses_for_update_skip_locked(self, mock_db, mock_quota):
        """Verify the query uses FOR UPDATE SKIP LOCKED."""
        mock_quota.return_value = None

        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = []
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        sync_contacts_to_mailwizz()

        first_call_sql = str(session.execute.call_args_list[0][0][0].text)
        assert "FOR UPDATE SKIP LOCKED" in first_call_sql

    @patch("scraper.jobs.sync_to_mailwizz.get_client")
    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_social_media_parsed_from_json_string(self, mock_db, mock_quota, mock_get_client):
        """Social media stored as JSON string should be parsed into fields."""
        contact = _make_validated_contact(
            20, "social@law.com",
            social_media=json.dumps({
                "facebook": "fb.com/test",
                "instagram": "@test",
                "linkedin": "li.com/test",
            }),
        )
        mock_quota.return_value = None

        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [contact]
        savepoint = MagicMock()
        session.begin_nested.return_value = savepoint
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        client = MagicMock()
        client.add_subscriber.return_value = {"success": True, "subscriber_uid": "s1"}
        mock_get_client.return_value = client

        sync_contacts_to_mailwizz()

        call_data = client.add_subscriber.call_args[1]["data"]
        assert call_data["FACEBOOK"] == "fb.com/test"
        assert call_data["INSTAGRAM"] == "@test"
        assert call_data["LINKEDIN"] == "li.com/test"

    @patch("scraper.jobs.sync_to_mailwizz.get_daily_quota_remaining")
    @patch("scraper.jobs.sync_to_mailwizz.get_db_session")
    def test_empty_batch_returns_zero_stats(self, mock_db, mock_quota):
        """No contacts ready -> all stats are 0."""
        mock_quota.return_value = None

        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = []
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        stats = sync_contacts_to_mailwizz()

        assert stats == {"success": 0, "failed": 0, "retries": 0, "held_warmup": 0}

    def test_constants(self):
        """Verify batch and retry constants."""
        assert BATCH_SIZE == 100
        assert MAX_RETRIES == 3
