"""
Google Search Spider - Discovers websites via Google Search queries.
Extracts result URLs then scrapes each for contact info.
Supports checkpoint/resume for interrupted jobs.
"""

import re
from urllib.parse import urlencode, urljoin, urlparse

import scrapy

from scraper.items import ContactItem
from scraper.integrations import serpapi_client
from scraper.utils.checkpoint import (
    load_checkpoint,
    mark_url_seen,
    save_checkpoint,
    update_progress,
)


class GoogleSearchSpider(scrapy.Spider):
    name = "google_search"

    EMAIL_RE = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )
    PHONE_RE = re.compile(
        r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}"
    )
    EMAIL_BLACKLIST = [
        "noreply@", "no-reply@", "donotreply@", "admin@", "webmaster@",
        "postmaster@", "hostmaster@", "info@example", "contact@example",
        "test@", "spam@", "abuse@",
    ]
    CONTACT_PAGE_PATTERNS = [
        "contact", "about", "team", "equipe", "a-propos",
        "nous-contacter", "our-team", "staff",
    ]
    SOCIAL_PATTERNS = {
        "facebook": "facebook.com/",
        "instagram": "instagram.com/",
        "linkedin": "linkedin.com/",
        "twitter": ("twitter.com/", "x.com/"),
        "youtube": "youtube.com/",
    }

    def __init__(
        self, job_id=None, query="", max_results=100,
        scrape_depth=2, country=None, language=None, resume="false",
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.query = query
        self.max_results = int(max_results)
        self.scrape_depth = int(scrape_depth)
        self.country = country
        self.language = language
        self.results_collected = 0
        self.contacts_found = 0
        self.resume = resume == "true"

    def start_requests(self):
        """Generate Google Search requests with pagination, respecting checkpoint."""
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

        for start in range(start_offset, self.max_results, 10):
            params = {"q": self.query, "start": start, "num": 10}
            if self.country:
                params["gl"] = self.country
            if self.language:
                params["lr"] = f"lang_{self.language}"
                params["hl"] = self.language

            url = f"https://www.google.com/search?{urlencode(params)}"
            yield scrapy.Request(
                url,
                callback=self.parse_search_results,
                meta={"search_start": start},
                errback=self.handle_error,
            )

    def parse_search_results(self, response):
        """Parse Google search results page, extract result URLs.
        Falls back to SerpAPI on 403/CAPTCHA."""
        page_start = response.meta.get("search_start", 0)

        # Detect Google block (CAPTCHA / 403)
        if response.status in (403, 429) or "captcha" in response.text.lower():
            self.logger.warning(
                f"Google blocked (HTTP {response.status}), trying SerpAPI fallback"
            )
            yield from self._serpapi_fallback(page_start)
            return

        found_any = False
        for result in response.css("div.g a::attr(href)").getall():
            if not result.startswith("http"):
                continue
            domain = urlparse(result).netloc
            if "google." in domain:
                continue
            if self.results_collected >= self.max_results:
                return

            found_any = True
            self.results_collected += 1
            yield scrapy.Request(
                result,
                callback=self.parse_site,
                meta={"depth": 0, "start_url": result},
                errback=self.handle_error,
            )

        # If Google returned a page but we found no results, likely a soft block
        if not found_any and serpapi_client.is_available():
            self.logger.warning("No results found in Google HTML, trying SerpAPI")
            yield from self._serpapi_fallback(page_start)

        # Save checkpoint after each search results page
        if self.job_id:
            progress = (page_start + 10) / self.max_results * 100
            save_checkpoint(int(self.job_id), {
                "last_page": page_start + 10,
                "results_collected": self.results_collected,
                "contacts_found": self.contacts_found,
            })
            update_progress(
                int(self.job_id), progress,
                pages=page_start // 10 + 1,
                contacts=self.contacts_found,
            )

    def parse_site(self, response):
        """Parse individual site for contacts, follow internal links."""
        current_depth = response.meta.get("depth", 0)
        start_url = response.meta.get("start_url", response.url)
        domain = urlparse(response.url).netloc

        # Mark URL as visited globally
        mark_url_seen(response.url, spider_name=self.name)

        yield from self._extract_contacts(response, start_url)

        if current_depth < self.scrape_depth:
            for link in response.css("a::attr(href)").getall():
                full_url = urljoin(response.url, link)
                if urlparse(full_url).netloc != domain:
                    continue
                link_lower = full_url.lower()
                is_contact_page = any(
                    p in link_lower for p in self.CONTACT_PAGE_PATTERNS
                )
                yield scrapy.Request(
                    full_url,
                    callback=self.parse_site,
                    meta={"depth": current_depth + 1, "start_url": start_url},
                    priority=0 if is_contact_page else 1,
                    dont_filter=False,
                    errback=self.handle_error,
                )

    def _extract_contacts(self, response, start_url):
        text = response.text
        domain = urlparse(response.url).netloc

        emails = set(self.EMAIL_RE.findall(text))
        emails = {
            e.lower() for e in emails
            if not any(bl in e.lower() for bl in self.EMAIL_BLACKLIST)
            and not e.endswith((".png", ".jpg", ".gif", ".css", ".js"))
        }

        # Extract phones (fixed: was missing)
        phones = set(self.PHONE_RE.findall(text))

        name = (
            response.css("h1::text").get("")
            or response.css("title::text").get("")
        ).strip()

        # Extract social media (fixed: was missing)
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
                "website": start_url,
                "address": None,
                "social_media": social,
                "source_type": "google_search",
                "source_url": response.url,
                "domain": domain,
                "keywords": self.query,
                "country": self.country,
                "job_id": self.job_id,
            })

    def _serpapi_fallback(self, page_start: int):
        """Use SerpAPI when Google blocks direct scraping."""
        if not serpapi_client.is_available():
            self.logger.error("SerpAPI key not configured, cannot fallback")
            return

        results = serpapi_client.search_google(
            query=self.query,
            country=self.country,
            language=self.language,
            start=page_start,
            num=10,
        )

        self.logger.info(f"SerpAPI returned {len(results)} results")

        for item in results:
            link = item.get("link", "")
            if not link or self.results_collected >= self.max_results:
                return
            domain = urlparse(link).netloc
            if "google." in domain:
                continue

            self.results_collected += 1
            yield scrapy.Request(
                link,
                callback=self.parse_site,
                meta={"depth": 0, "start_url": link},
                errback=self.handle_error,
            )

    def handle_error(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url} - {failure.value}")
