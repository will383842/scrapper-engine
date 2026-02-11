"""
Google Maps Spider - Extracts business contacts from Google Maps listings.
Uses Google Maps search URLs to find businesses by category + location.
Supports checkpoint/resume for interrupted jobs.
"""

import json
import re
from urllib.parse import urlencode

import scrapy

from scraper.items import ContactItem
from scraper.integrations import serpapi_client
from scraper.utils.checkpoint import (
    load_checkpoint,
    mark_url_seen,
    save_checkpoint,
    update_progress,
)


class GoogleMapsSpider(scrapy.Spider):
    name = "google_maps"

    EMAIL_RE = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )
    PHONE_RE = re.compile(
        r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}"
    )
    EMAIL_BLACKLIST = [
        "noreply@", "no-reply@", "admin@", "webmaster@",
        "postmaster@", "test@", "spam@",
    ]
    SOCIAL_PATTERNS = {
        "facebook": "facebook.com/",
        "instagram": "instagram.com/",
        "linkedin": "linkedin.com/",
        "twitter": ("twitter.com/", "x.com/"),
        "youtube": "youtube.com/",
    }

    def __init__(
        self, job_id=None, query="", location="",
        max_results=100, country=None, language=None, resume="false",
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.query = query
        self.location = location
        self.max_results = int(max_results)
        self.country = country
        self.language = language
        self.results_collected = 0
        self.contacts_found = 0
        self.resume = resume == "true"

    def start_requests(self):
        """Search Google Maps for businesses with pagination, respecting checkpoint."""
        start_offset = 0
        if self.resume and self.job_id:
            checkpoint = load_checkpoint(int(self.job_id))
            if checkpoint:
                start_offset = checkpoint.get("last_page", 0)
                self.results_collected = checkpoint.get("results_collected", 0)
                self.contacts_found = checkpoint.get("contacts_found", 0)
                self.logger.info(
                    f"Resuming from page {start_offset}, "
                    f"{self.results_collected} results already collected"
                )

        search_query = f"{self.query} {self.location}".strip()
        for start in range(start_offset, self.max_results, 20):
            params = {"q": search_query, "tbm": "lcl", "start": start}
            if self.country:
                params["gl"] = self.country
            if self.language:
                params["hl"] = self.language

            url = f"https://www.google.com/search?{urlencode(params)}"
            yield scrapy.Request(
                url,
                callback=self.parse_maps_results,
                meta={"search_start": start},
                errback=self.handle_error,
            )

    def parse_maps_results(self, response):
        """Parse Google local results for business info.
        Falls back to SerpAPI on 403/CAPTCHA."""
        page_start = response.meta.get("search_start", 0)

        # Detect Google block
        if response.status in (403, 429) or "captcha" in response.text.lower():
            self.logger.warning(
                f"Google Maps blocked (HTTP {response.status}), trying SerpAPI fallback"
            )
            yield from self._serpapi_fallback()
            return

        found_any = False
        for listing in response.css("div.VkpGBb a::attr(href)").getall():
            if self.results_collected >= self.max_results:
                return
            found_any = True
            self.results_collected += 1
            yield scrapy.Request(
                listing,
                callback=self.parse_business_page,
                errback=self.handle_error,
            )

        yield from self._extract_from_page_data(response)

        if not found_any and serpapi_client.is_available():
            self.logger.warning("No Maps results found in HTML, trying SerpAPI")
            yield from self._serpapi_fallback()

        # Save checkpoint after each page
        if self.job_id:
            progress = (page_start + 20) / self.max_results * 100
            save_checkpoint(int(self.job_id), {
                "last_page": page_start + 20,
                "results_collected": self.results_collected,
                "contacts_found": self.contacts_found,
            })
            update_progress(
                int(self.job_id), progress,
                pages=page_start // 20 + 1,
                contacts=self.contacts_found,
            )

    def parse_business_page(self, response):
        """Parse individual business website for contacts."""
        text = response.text
        mark_url_seen(response.url, spider_name=self.name)

        emails = set(self.EMAIL_RE.findall(text))
        emails = {
            e.lower() for e in emails
            if not any(bl in e.lower() for bl in self.EMAIL_BLACKLIST)
        }

        name = (
            response.css("h1::text").get("")
            or response.css("title::text").get("")
        ).strip()

        phones = set(self.PHONE_RE.findall(text))

        # Extract social media (fixed: was empty)
        social = {}
        for link in response.css("a::attr(href)").getall():
            link_lower = link.lower()
            for platform, patterns in self.SOCIAL_PATTERNS.items():
                if isinstance(patterns, tuple):
                    if any(p in link_lower for p in patterns):
                        social[platform] = link
                elif patterns in link_lower:
                    social[platform] = link

        for email in emails:
            self.contacts_found += 1
            yield ContactItem({
                "email": email,
                "name": name[:255] if name else None,
                "phone": list(phones)[0] if phones else None,
                "website": response.url,
                "address": None,
                "social_media": social,
                "source_type": "google_maps",
                "source_url": response.url,
                "domain": response.url.split("/")[2] if "/" in response.url else "",
                "keywords": self.query,
                "country": self.country,
                "job_id": self.job_id,
            })

    def _extract_from_page_data(self, response):
        """Try to extract structured business data from Google's JSON."""
        try:
            for script in response.css("script::text").getall():
                if "business" not in script.lower():
                    continue
                emails = set(self.EMAIL_RE.findall(script))
                for email in emails:
                    self.contacts_found += 1
                    yield ContactItem({
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
                    })
        except Exception as e:
            self.logger.debug(f"Could not parse structured data: {e}")

    def _serpapi_fallback(self):
        """Use SerpAPI for Google Maps when direct scraping is blocked."""
        if not serpapi_client.is_available():
            self.logger.error("SerpAPI key not configured, cannot fallback")
            return

        results = serpapi_client.search_google_maps(
            query=self.query,
            location=self.location,
            language=self.language,
        )

        self.logger.info(f"SerpAPI Maps returned {len(results)} results")

        for item in results:
            website = item.get("website") or item.get("link", "")
            if not website or self.results_collected >= self.max_results:
                return

            self.results_collected += 1

            # If we got phone/address directly from SerpAPI, yield contact immediately
            email_matches = set(self.EMAIL_RE.findall(str(item)))
            if email_matches:
                for email in email_matches:
                    self.contacts_found += 1
                    yield ContactItem({
                        "email": email.lower(),
                        "name": item.get("title"),
                        "phone": item.get("phone"),
                        "website": website,
                        "address": item.get("address"),
                        "social_media": {},
                        "source_type": "google_maps",
                        "source_url": website,
                        "domain": website.split("/")[2] if "/" in website else "",
                        "keywords": self.query,
                        "country": self.country,
                        "job_id": self.job_id,
                    })
            elif website.startswith("http"):
                # No email in SerpAPI data, scrape the website
                yield scrapy.Request(
                    website,
                    callback=self.parse_business_page,
                    errback=self.handle_error,
                )

    def handle_error(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url} - {failure.value}")
