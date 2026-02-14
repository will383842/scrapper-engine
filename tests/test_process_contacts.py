"""Tests for process_contacts cron job."""

import json
from unittest.mock import patch, MagicMock, call

import pytest

from scraper.jobs.process_contacts import process_pending_contacts, BATCH_SIZE


def _make_contact(id_: int, email: str, **overrides):
    """Build a fake scraped_contact row."""
    base = {
        "id": id_,
        "email": email,
        "name": "Test User",
        "phone": "+33612345678",
        "website": "https://example.com",
        "address": "1 Rue Test, Paris",
        "social_media": "{}",
        "source_type": "google_search",
        "source_url": "https://example.com/contact",
        "domain": "example.com",
        "country": "FR",
        "keywords": "avocat international paris",
        "job_id": 1,
    }
    base.update(overrides)
    return base


class TestProcessPendingContacts:
    """Test the main process_pending_contacts function."""

    @patch("scraper.jobs.process_contacts.get_routing_info")
    @patch("scraper.jobs.process_contacts.generate_tags")
    @patch("scraper.jobs.process_contacts.determine_platform")
    @patch("scraper.jobs.process_contacts.categorize")
    @patch("scraper.jobs.process_contacts.validate_phone")
    @patch("scraper.jobs.process_contacts.clean_phone")
    @patch("scraper.jobs.process_contacts.validate_email")
    @patch("scraper.jobs.process_contacts.get_db_session")
    def test_validates_and_inserts_contact(
        self, mock_db, mock_validate_email, mock_clean_phone,
        mock_validate_phone, mock_categorize, mock_platform,
        mock_tags, mock_routing,
    ):
        """Happy path: valid contact is validated and inserted."""
        contact = _make_contact(1, "avocat@lawfirm.com")

        session = MagicMock()
        # 1st execute: fetch pending contacts
        session.execute.return_value.mappings.return_value.all.return_value = [contact]
        # 2nd+: duplicate check returns None (no dup)
        # 3rd: blacklist check returns None (not blacklisted)
        # We need separate return values per call
        execute_results = [
            # Fetch pending contacts
            MagicMock(mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[contact])))),
            # Validate email -> used via validate_email mock
            # Duplicate check -> no match
            MagicMock(first=MagicMock(return_value=None)),
            # Blacklist check -> not blacklisted
            MagicMock(first=MagicMock(return_value=None)),
            # INSERT validated_contacts
            MagicMock(),
            # UPDATE scraped_contacts status
            MagicMock(),
        ]
        session.execute.side_effect = execute_results
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_validate_email.return_value = True
        mock_clean_phone.return_value = "+33612345678"
        mock_validate_phone.return_value = True
        mock_categorize.return_value = "avocat"
        mock_platform.return_value = "sos-expat"
        mock_tags.return_value = ["avocat", "google_search", "FR"]
        mock_routing.return_value = {
            "list_id": 10,
            "list_name": "Avocats",
            "auto_tags": [],
            "template_default": "avocat_intro",
        }

        stats = process_pending_contacts()

        assert stats["processed"] == 1
        assert stats["validated"] == 1
        assert stats["rejected"] == 0
        assert stats["duplicates"] == 0
        # Should have 5 execute calls: fetch, dup check, blacklist, insert, update
        assert session.execute.call_count == 5

    @patch("scraper.jobs.process_contacts.validate_email")
    @patch("scraper.jobs.process_contacts.get_db_session")
    def test_rejects_invalid_email(self, mock_db, mock_validate_email):
        """Invalid email -> rejected, no insertion."""
        contact = _make_contact(2, "bad-email")

        session = MagicMock()
        execute_results = [
            MagicMock(mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[contact])))),
            MagicMock(),  # UPDATE to rejected
        ]
        session.execute.side_effect = execute_results
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_validate_email.return_value = False

        stats = process_pending_contacts()

        assert stats["processed"] == 1
        assert stats["rejected"] == 1
        assert stats["validated"] == 0

    @patch("scraper.jobs.process_contacts.validate_email")
    @patch("scraper.jobs.process_contacts.get_db_session")
    def test_detects_duplicate_contact(self, mock_db, mock_validate_email):
        """Duplicate email in validated_contacts -> marked as duplicate."""
        contact = _make_contact(3, "existing@lawfirm.com")

        session = MagicMock()
        execute_results = [
            MagicMock(mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[contact])))),
            # Duplicate check -> found existing
            MagicMock(first=MagicMock(return_value={"id": 99})),
            MagicMock(),  # UPDATE to rejected
        ]
        session.execute.side_effect = execute_results
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_validate_email.return_value = True

        stats = process_pending_contacts()

        assert stats["processed"] == 1
        assert stats["duplicates"] == 1
        assert stats["validated"] == 0

    @patch("scraper.jobs.process_contacts.validate_email")
    @patch("scraper.jobs.process_contacts.get_db_session")
    def test_rejects_blacklisted_domain(self, mock_db, mock_validate_email):
        """Email on blacklisted domain -> rejected."""
        contact = _make_contact(4, "user@spammy-domain.com")

        session = MagicMock()
        execute_results = [
            MagicMock(mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[contact])))),
            # Duplicate check -> not found
            MagicMock(first=MagicMock(return_value=None)),
            # Blacklist check -> blacklisted
            MagicMock(first=MagicMock(return_value={"id": 1})),
            MagicMock(),  # UPDATE to rejected
        ]
        session.execute.side_effect = execute_results
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        mock_validate_email.return_value = True

        stats = process_pending_contacts()

        assert stats["processed"] == 1
        assert stats["rejected"] == 1
        assert stats["validated"] == 0

    @patch("scraper.jobs.process_contacts.get_db_session")
    def test_empty_batch_returns_zero_stats(self, mock_db):
        """No pending contacts -> all stats are 0."""
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = []
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        stats = process_pending_contacts()

        assert stats == {"processed": 0, "validated": 0, "rejected": 0, "duplicates": 0}

    @patch("scraper.jobs.process_contacts.get_routing_info")
    @patch("scraper.jobs.process_contacts.generate_tags")
    @patch("scraper.jobs.process_contacts.determine_platform")
    @patch("scraper.jobs.process_contacts.categorize")
    @patch("scraper.jobs.process_contacts.validate_phone")
    @patch("scraper.jobs.process_contacts.clean_phone")
    @patch("scraper.jobs.process_contacts.validate_email")
    @patch("scraper.jobs.process_contacts.get_db_session")
    def test_batch_processing_mixed_results(
        self, mock_db, mock_validate_email, mock_clean_phone,
        mock_validate_phone, mock_categorize, mock_platform,
        mock_tags, mock_routing,
    ):
        """Multiple contacts: mix of valid, invalid, duplicate."""
        contacts = [
            _make_contact(10, "valid@law.com"),
            _make_contact(11, "bad-email"),
            _make_contact(12, "dup@law.com"),
        ]

        session = MagicMock()

        # validate_email: True for 1st and 3rd, False for 2nd
        mock_validate_email.side_effect = [True, False, True]
        mock_clean_phone.return_value = "+33612345678"
        mock_validate_phone.return_value = True
        mock_categorize.return_value = "avocat"
        mock_platform.return_value = "sos-expat"
        mock_tags.return_value = ["avocat"]
        mock_routing.return_value = {
            "list_id": 10, "list_name": "Avocats",
            "auto_tags": [], "template_default": None,
        }

        execute_results = [
            # Fetch batch
            MagicMock(mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=contacts)))),
            # Contact 10: dup check -> no dup
            MagicMock(first=MagicMock(return_value=None)),
            # Contact 10: blacklist check -> clean
            MagicMock(first=MagicMock(return_value=None)),
            # Contact 10: INSERT validated_contacts
            MagicMock(),
            # Contact 10: UPDATE scraped_contacts
            MagicMock(),
            # Contact 11: UPDATE to rejected (invalid email)
            MagicMock(),
            # Contact 12: dup check -> found
            MagicMock(first=MagicMock(return_value={"id": 99})),
            # Contact 12: UPDATE to rejected (duplicate)
            MagicMock(),
        ]
        session.execute.side_effect = execute_results
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        stats = process_pending_contacts()

        assert stats["processed"] == 3
        assert stats["validated"] == 1
        assert stats["rejected"] == 1
        assert stats["duplicates"] == 1

    @patch("scraper.jobs.process_contacts.get_db_session")
    def test_select_uses_for_update_skip_locked(self, mock_db):
        """Verify the query uses FOR UPDATE SKIP LOCKED to prevent races."""
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = []
        mock_db.return_value.__enter__ = MagicMock(return_value=session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        process_pending_contacts()

        # Check the first execute call contains FOR UPDATE SKIP LOCKED
        first_call_sql = str(session.execute.call_args_list[0][0][0].text)
        assert "FOR UPDATE SKIP LOCKED" in first_call_sql

    @patch("scraper.jobs.process_contacts.get_db_session")
    def test_batch_size_is_1000(self, mock_db):
        """Verify BATCH_SIZE constant."""
        assert BATCH_SIZE == 1000
