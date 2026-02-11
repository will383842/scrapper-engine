"""Tests for the WHOIS lookup module - pure function tests only."""

from datetime import datetime

import pytest
from unittest.mock import MagicMock

from scraper.modules.whois_lookup import _detect_privacy, _detect_cloudflare, _parse_date


# ---------------------------------------------------------------------------
# _detect_privacy
# ---------------------------------------------------------------------------

class TestDetectPrivacy:
    """Tests for _detect_privacy() helper."""

    def _make_whois(self, text=""):
        """Create a mock whois data object."""
        obj = MagicMock()
        obj.text = text
        return obj

    def test_detect_privacy_whoisguard(self):
        """WhoisGuard in the registrant org should be detected as private."""
        w = self._make_whois()
        assert _detect_privacy(w, name="", org="WhoisGuard Protected", email="") is True

    def test_detect_privacy_redacted(self):
        """GDPR-redacted names should be detected as private."""
        w = self._make_whois()
        assert _detect_privacy(w, name="REDACTED FOR PRIVACY", org="", email="") is True

    def test_detect_privacy_normal(self):
        """A normal registrant should NOT be flagged as private."""
        w = self._make_whois()
        result = _detect_privacy(
            w,
            name="John Doe",
            org="Doe Industries",
            email="john@doe-industries.com",
        )
        assert result is False

    def test_detect_privacy_domains_by_proxy(self):
        """'Domains By Proxy' in the org should be detected."""
        w = self._make_whois()
        assert _detect_privacy(w, name="", org="Domains By Proxy, LLC", email="") is True

    def test_detect_privacy_in_raw_text(self):
        """Privacy indicator in the raw WHOIS text (not the parsed fields)."""
        w = self._make_whois(text="Registrant Name: REDACTED FOR PRIVACY")
        assert _detect_privacy(w, name="", org="", email="") is True


# ---------------------------------------------------------------------------
# _detect_cloudflare
# ---------------------------------------------------------------------------

class TestDetectCloudflare:
    """Tests for _detect_cloudflare() helper."""

    def _make_whois(self, name_servers=None):
        obj = MagicMock()
        obj.name_servers = name_servers
        return obj

    def test_detect_cloudflare_registrar(self):
        """Cloudflare, Inc. as registrar should be detected."""
        w = self._make_whois()
        assert _detect_cloudflare("Cloudflare, Inc.", w) is True

    def test_detect_cloudflare_nameservers(self):
        """Cloudflare nameservers should be detected even with a different registrar."""
        w = self._make_whois(name_servers=["ada.ns.cloudflare.com", "bob.ns.cloudflare.com"])
        assert _detect_cloudflare("NameCheap, Inc.", w) is True

    def test_detect_cloudflare_normal(self):
        """A domain not using Cloudflare should return False."""
        w = self._make_whois(name_servers=["ns1.godaddy.com", "ns2.godaddy.com"])
        assert _detect_cloudflare("GoDaddy.com, LLC", w) is False

    def test_detect_cloudflare_no_nameservers(self):
        """If nameservers are None, only registrar should be checked."""
        w = self._make_whois(name_servers=None)
        assert _detect_cloudflare("GoDaddy.com, LLC", w) is False

    def test_detect_cloudflare_single_nameserver_string(self):
        """A single nameserver string (not a list) containing cloudflare should match."""
        w = self._make_whois(name_servers="ada.ns.cloudflare.com")
        assert _detect_cloudflare("NameCheap, Inc.", w) is True


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    """Tests for _parse_date() helper."""

    def test_parse_date_datetime(self):
        """A datetime object should be returned as an ISO string."""
        dt = datetime(2023, 6, 15, 10, 30, 0)
        assert _parse_date(dt) == "2023-06-15T10:30:00"

    def test_parse_date_string(self):
        """A string date should be returned as-is (stringified)."""
        assert _parse_date("2023-06-15") == "2023-06-15"

    def test_parse_date_list(self):
        """A list of dates should use the first element."""
        dates = [datetime(2023, 1, 1), datetime(2024, 1, 1)]
        result = _parse_date(dates)
        assert result == "2023-01-01T00:00:00"

    def test_parse_date_none(self):
        """None input should return None."""
        assert _parse_date(None) is None

    def test_parse_date_empty_list(self):
        """An empty value (falsy) should return None."""
        assert _parse_date("") is None
        assert _parse_date(0) is None
