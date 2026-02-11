"""
Google Maps Spider - Extracts business contacts from Google Maps listings.
Uses Google Maps search URLs to find businesses by category + location.
"""

import json
import re
from urllib.parse import urlencode

import scrapy


class GoogleMapsSpider(scrapy.Spider):
    name = "google_maps"

    EMAIL_RE = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )

    def __init__(
        self, job_id=None, query="", location="",
        max_results=100, country=None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.query = query
        self.location = location
        self.max_results = int(max_results)
        self.country = country
        self.results_collected = 0

    def start_requests(self):
        """Search Google Maps for businesses."""
        search_query = f"{self.query} {self.location}".strip()
        params = {"q": search_query, "tbm": "lcl"}
        if self.country:
            params["gl"] = self.country

        url = f"https://www.google.com/search?{urlencode(params)}"
        yield scrapy.Request(
            url,
            callback=self.parse_maps_results,
            errback=self.handle_error,
        )

    def parse_maps_results(self, response):
        """Parse Google local results for business info."""
        # Extract business listing links
        for listing in response.css("div.VkpGBb a::attr(href)").getall():
            if self.results_collected >= self.max_results:
                return

            self.results_collected += 1
            yield scrapy.Request(
                listing,
                callback=self.parse_business_page,
                errback=self.handle_error,
            )

        # Also extract from Google business profile data in page source
        yield from self._extract_from_page_data(response)

    def parse_business_page(self, response):
        """Parse individual business website for contacts."""
        text = response.text

        emails = set(self.EMAIL_RE.findall(text))
        emails = {
            e.lower() for e in emails
            if not any(
                bl in e.lower()
                for bl in ["noreply@", "no-reply@", "admin@", "webmaster@"]
            )
        }

        name = (
            response.css("h1::text").get("")
            or response.css("title::text").get("")
        ).strip()

        phone_match = re.search(
            r'(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}',
            text
        )

        for email in emails:
            yield {
                "email": email,
                "name": name[:255] if name else None,
                "phone": phone_match.group() if phone_match else None,
                "website": response.url,
                "address": None,
                "social_media": {},
                "source_type": "google_maps",
                "source_url": response.url,
                "domain": response.url.split("/")[2] if "/" in response.url else "",
                "keywords": self.query,
                "country": self.country,
                "job_id": self.job_id,
            }

    def _extract_from_page_data(self, response):
        """Try to extract structured business data from Google's JSON."""
        try:
            # Google embeds business data in script tags
            for script in response.css("script::text").getall():
                if "business" not in script.lower():
                    continue
                emails = set(self.EMAIL_RE.findall(script))
                for email in emails:
                    yield {
                        "email": email.lower(),
                        "name": None,
                        "phone": None,
                        "website": None,
                        "address": None,
                        "social_media": {},
                        "source_type": "google_maps",
                        "source_url": response.url,
                        "domain": "",
                        "keywords": self.query,
                        "country": self.country,
                        "job_id": self.job_id,
                    }
        except Exception as e:
            self.logger.debug(f"Could not parse structured data: {e}")

    def handle_error(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url} - {failure.value}")
