"""Tests for Scrapy spiders: GoogleSearchSpider, GoogleMapsSpider, GenericUrlSpider."""

import json
import re

import pytest
from unittest.mock import MagicMock, patch

from scrapy.http import HtmlResponse, Request
from scraper.items import ContactItem


def _fake_response(url, body, meta=None):
    """Create a fake Scrapy HtmlResponse for testing."""
    request = Request(url=url, meta=meta or {})
    return HtmlResponse(
        url=url,
        body=body.encode("utf-8"),
        request=request,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# GoogleSearchSpider
# ---------------------------------------------------------------------------

class TestGoogleSearchSpider:
    """Tests for GoogleSearchSpider."""

    def _make_spider(self, **kwargs):
        from scraper.spiders.google_search_spider import GoogleSearchSpider

        defaults = {
            "job_id": 1,
            "query": "avocat paris",
            "max_results": 30,
            "country": "FR",
        }
        defaults.update(kwargs)
        return GoogleSearchSpider(**defaults)

    def test_start_requests_pagination(self):
        """start_requests should generate one request per page of 10 results."""
        spider = self._make_spider(max_results=30)
        requests = list(spider.start_requests())

        # max_results=30 -> range(0, 30, 10) -> 3 pages
        assert len(requests) == 3

        # Verify the 'start' param increments by 10
        urls = [r.url for r in requests]
        assert "start=0" in urls[0]
        assert "start=10" in urls[1]
        assert "start=20" in urls[2]

        # Verify country parameter is in the URL
        for url in urls:
            assert "gl=FR" in url

    def test_start_requests_no_country(self):
        """When no country is set, the gl parameter should not appear."""
        spider = self._make_spider(max_results=10, country=None)
        requests = list(spider.start_requests())
        assert len(requests) == 1
        assert "gl=" not in requests[0].url

    def test_extract_contacts_finds_emails(self):
        """_extract_contacts should yield ContactItems for emails found in the page."""
        spider = self._make_spider()

        html = """
        <html>
        <head><title>Cabinet Dupont</title></head>
        <body>
            <h1>Cabinet Dupont - Avocats</h1>
            <p>Contact: jean.dupont@cabinet-dupont.fr</p>
            <p>Also: marie.martin@lawfirm.com</p>
        </body>
        </html>
        """
        response = _fake_response(
            "https://www.cabinet-dupont.fr/contact",
            html,
            meta={"depth": 0, "start_url": "https://www.cabinet-dupont.fr"},
        )

        items = list(spider._extract_contacts(response, "https://www.cabinet-dupont.fr"))
        emails = {item["email"] for item in items}

        assert "jean.dupont@cabinet-dupont.fr" in emails
        assert "marie.martin@lawfirm.com" in emails
        assert len(items) >= 2

        # Each item should be a ContactItem
        for item in items:
            assert isinstance(item, ContactItem)
            assert item["source_type"] == "google_search"
            assert item["job_id"] == 1

    def test_extract_contacts_filters_blacklisted(self):
        """Blacklisted prefixes like noreply@ should be filtered out."""
        spider = self._make_spider()

        html = """
        <html>
        <body>
            <p>noreply@example.com</p>
            <p>webmaster@example.com</p>
            <p>real.person@example.com</p>
        </body>
        </html>
        """
        response = _fake_response(
            "https://example.com",
            html,
            meta={"depth": 0, "start_url": "https://example.com"},
        )

        items = list(spider._extract_contacts(response, "https://example.com"))
        emails = {item["email"] for item in items}

        assert "noreply@example.com" not in emails
        assert "webmaster@example.com" not in emails
        assert "real.person@example.com" in emails

    def test_extract_contacts_gets_phones(self):
        """_extract_contacts should extract phone numbers."""
        spider = self._make_spider()

        html = """
        <html>
        <body>
            <h1>Test Firm</h1>
            <p>Email: contact@firm.com</p>
            <p>Phone: +33 1 42 68 53 00</p>
        </body>
        </html>
        """
        response = _fake_response(
            "https://firm.com",
            html,
            meta={"depth": 0, "start_url": "https://firm.com"},
        )

        items = list(spider._extract_contacts(response, "https://firm.com"))
        assert len(items) >= 1
        assert items[0].get("phone") is not None

    def test_extract_contacts_gets_social_media(self):
        """_extract_contacts should extract social media links."""
        spider = self._make_spider()

        html = """
        <html>
        <body>
            <p>Email: contact@firm.com</p>
            <a href="https://facebook.com/firmpage">FB</a>
            <a href="https://linkedin.com/company/firm">LI</a>
        </body>
        </html>
        """
        response = _fake_response(
            "https://firm.com",
            html,
            meta={"depth": 0, "start_url": "https://firm.com"},
        )

        items = list(spider._extract_contacts(response, "https://firm.com"))
        assert len(items) >= 1
        social = items[0].get("social_media", {})
        assert "facebook" in social
        assert "linkedin" in social

    @patch("scraper.spiders.google_search_spider.load_checkpoint")
    def test_resume_starts_from_checkpoint(self, mock_load):
        """With resume=true, spider should load checkpoint and set start_offset."""
        mock_load.return_value = {
            "last_page": 20,
            "results_collected": 15,
            "contacts_found": 8,
        }

        spider = self._make_spider(resume="true", max_results=50)
        requests = list(spider.start_requests())

        # Should skip pages 0 and 10, start from 20
        urls = [r.url for r in requests]
        assert all("start=0" not in u for u in urls)
        assert all("start=10" not in u for u in urls)
        assert any("start=20" in u for u in urls)

        # Counters should be restored
        assert spider.results_collected == 15
        assert spider.contacts_found == 8


# ---------------------------------------------------------------------------
# GoogleMapsSpider
# ---------------------------------------------------------------------------

class TestGoogleMapsSpider:
    """Tests for GoogleMapsSpider."""

    def _make_spider(self, **kwargs):
        from scraper.spiders.google_maps_spider import GoogleMapsSpider

        defaults = {
            "job_id": 2,
            "query": "avocat",
            "location": "Paris",
            "max_results": 40,
            "country": "FR",
        }
        defaults.update(kwargs)
        return GoogleMapsSpider(**defaults)

    def test_start_requests_pagination(self):
        """start_requests should generate one request per page of 20 results."""
        spider = self._make_spider(max_results=40)
        requests = list(spider.start_requests())

        # max_results=40 -> range(0, 40, 20) -> 2 pages
        assert len(requests) == 2

        urls = [r.url for r in requests]
        assert "start=0" in urls[0]
        assert "start=20" in urls[1]
        # tbm=lcl for local results
        for url in urls:
            assert "tbm=lcl" in url
            assert "gl=FR" in url

    def test_parse_business_page_extracts_email(self):
        """parse_business_page should yield ContactItems for emails found on a business page."""
        spider = self._make_spider()

        html = """
        <html>
        <head><title>Cabinet Martin</title></head>
        <body>
            <h1>Cabinet Martin</h1>
            <p>Email: contact@cabinet-martin.fr</p>
            <p>Tel: +33 1 23 45 67 89</p>
        </body>
        </html>
        """
        response = _fake_response("https://www.cabinet-martin.fr", html)

        items = list(spider.parse_business_page(response))
        assert len(items) >= 1

        item = items[0]
        assert isinstance(item, ContactItem)
        assert item["email"] == "contact@cabinet-martin.fr"
        assert item["source_type"] == "google_maps"
        assert item["job_id"] == 2
        # Name should be extracted from h1
        assert "Cabinet Martin" in (item["name"] or "")

    def test_parse_business_page_filters_noreply(self):
        """noreply@ emails should be filtered out."""
        spider = self._make_spider()

        html = """
        <html>
        <body>
            <p>noreply@example.com</p>
            <p>real@example.com</p>
        </body>
        </html>
        """
        response = _fake_response("https://example.com", html)

        items = list(spider.parse_business_page(response))
        emails = {item["email"] for item in items}
        assert "noreply@example.com" not in emails
        assert "real@example.com" in emails

    @patch("scraper.spiders.google_maps_spider.load_checkpoint")
    def test_resume_starts_from_checkpoint(self, mock_load):
        """With resume=true, spider should restore checkpoint state."""
        mock_load.return_value = {
            "last_page": 20,
            "results_collected": 10,
            "contacts_found": 5,
        }

        spider = self._make_spider(resume="true", max_results=60)
        requests = list(spider.start_requests())

        # Should skip page 0, start from 20
        urls = [r.url for r in requests]
        assert all("start=0" not in u for u in urls)
        assert any("start=20" in u for u in urls)

        # Counters should be restored
        assert spider.results_collected == 10
        assert spider.contacts_found == 5


# ---------------------------------------------------------------------------
# GenericUrlSpider
# ---------------------------------------------------------------------------

class TestGenericUrlSpider:
    """Tests for GenericUrlSpider."""

    def _make_spider(self, **kwargs):
        from scraper.spiders.generic_url_spider import GenericUrlSpider

        defaults = {
            "job_id": 3,
            "urls": ["https://site1.com", "https://site2.com"],
            "scrape_depth": 2,
        }
        defaults.update(kwargs)
        return GenericUrlSpider(**defaults)

    def test_start_requests_urls(self):
        """start_requests should yield one request per URL in the urls list."""
        spider = self._make_spider(
            urls=["https://site1.com", "https://site2.com", "https://site3.com"]
        )
        requests = list(spider.start_requests())

        assert len(requests) == 3
        urls = [r.url for r in requests]
        assert "https://site1.com" in urls
        assert "https://site2.com" in urls
        assert "https://site3.com" in urls

    def test_start_requests_empty_urls(self):
        """An empty urls list should yield no requests."""
        spider = self._make_spider(urls=[])
        requests = list(spider.start_requests())
        assert len(requests) == 0

    def test_extract_contacts_filters_blacklisted(self):
        """Blacklisted email prefixes should be filtered from results."""
        spider = self._make_spider()

        html = """
        <html>
        <head><title>Test Site</title></head>
        <body>
            <h1>Test Corp</h1>
            <p>admin@test.com</p>
            <p>postmaster@test.com</p>
            <p>abuse@test.com</p>
            <p>john.smith@test.com</p>
            <a href="https://facebook.com/testcorp">Facebook</a>
            <a href="https://linkedin.com/company/testcorp">LinkedIn</a>
        </body>
        </html>
        """
        response = _fake_response(
            "https://test.com/about",
            html,
            meta={"depth": 0, "start_url": "https://test.com"},
        )

        items = list(spider._extract_contacts(response, "https://test.com"))
        emails = {item["email"] for item in items}

        assert "admin@test.com" not in emails
        assert "postmaster@test.com" not in emails
        assert "abuse@test.com" not in emails
        assert "john.smith@test.com" in emails

        # Verify social media extraction for the valid item
        for item in items:
            if item["email"] == "john.smith@test.com":
                assert "facebook" in item.get("social_media", {})
                assert "linkedin" in item.get("social_media", {})

    def test_extract_contacts_filters_file_extensions(self):
        """Emails ending in image/css/js extensions should be filtered."""
        spider = self._make_spider()

        html = """
        <html>
        <body>
            <p>icon@site.png</p>
            <p>style@site.css</p>
            <p>valid@site.com</p>
        </body>
        </html>
        """
        response = _fake_response(
            "https://site.com",
            html,
            meta={"depth": 0, "start_url": "https://site.com"},
        )

        items = list(spider._extract_contacts(response, "https://site.com"))
        emails = {item["email"] for item in items}

        assert "icon@site.png" not in emails
        assert "style@site.css" not in emails
        assert "valid@site.com" in emails

    @patch("scraper.spiders.generic_url_spider.get_completed_urls_for_job")
    @patch("scraper.spiders.generic_url_spider.load_checkpoint")
    def test_resume_skips_completed_urls(self, mock_load, mock_completed):
        """With resume=true, spider should skip already-scraped URLs."""
        mock_load.return_value = {
            "urls_completed": 1,
            "contacts_found": 3,
        }
        mock_completed.return_value = {"https://site1.com"}

        spider = self._make_spider(
            urls=["https://site1.com", "https://site2.com", "https://site3.com"],
            resume="true",
        )
        requests = list(spider.start_requests())

        # site1.com already completed -> should be skipped
        urls = [r.url for r in requests]
        assert "https://site1.com" not in urls
        assert "https://site2.com" in urls
        assert "https://site3.com" in urls
        assert len(requests) == 2

        # Counters should be restored
        assert spider.urls_completed == 1
        assert spider.contacts_found == 3

    @patch("scraper.spiders.generic_url_spider.get_completed_urls_for_job")
    @patch("scraper.spiders.generic_url_spider.load_checkpoint")
    def test_resume_no_checkpoint_runs_all(self, mock_load, mock_completed):
        """With resume=true but no checkpoint, all URLs should run."""
        mock_load.return_value = {}
        mock_completed.return_value = set()

        spider = self._make_spider(
            urls=["https://site1.com", "https://site2.com"],
            resume="true",
        )
        requests = list(spider.start_requests())

        assert len(requests) == 2
