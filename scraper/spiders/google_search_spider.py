"""
Google Search Spider - Discovers websites via Google Search queries.
Extracts result URLs then scrapes each for contact info.
"""

import re
from urllib.parse import urlencode, urljoin, urlparse

import scrapy


class GoogleSearchSpider(scrapy.Spider):
    name = "google_search"

    EMAIL_RE = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )
    EMAIL_BLACKLIST = [
        "noreply@", "no-reply@", "donotreply@", "admin@", "webmaster@",
        "postmaster@", "hostmaster@", "info@example", "contact@example",
        "test@", "spam@", "abuse@",
    ]
    CONTACT_PAGE_PATTERNS = [
        "contact", "about", "team", "equipe", "a-propos",
    ]

    def __init__(
        self, job_id=None, query="", max_results=100,
        scrape_depth=2, country=None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.query = query
        self.max_results = int(max_results)
        self.scrape_depth = int(scrape_depth)
        self.country = country
        self.results_collected = 0

    def start_requests(self):
        """Generate Google Search requests with pagination."""
        for start in range(0, self.max_results, 10):
            params = {
                "q": self.query,
                "start": start,
                "num": 10,
            }
            if self.country:
                params["gl"] = self.country

            url = f"https://www.google.com/search?{urlencode(params)}"
            yield scrapy.Request(
                url,
                callback=self.parse_search_results,
                meta={"search_start": start},
                errback=self.handle_error,
            )

    def parse_search_results(self, response):
        """Parse Google search results page, extract result URLs."""
        # Extract organic result links
        for result in response.css("div.g a::attr(href)").getall():
            if not result.startswith("http"):
                continue

            domain = urlparse(result).netloc
            # Skip Google's own pages
            if "google." in domain:
                continue

            if self.results_collected >= self.max_results:
                return

            self.results_collected += 1
            yield scrapy.Request(
                result,
                callback=self.parse_site,
                meta={"depth": 0, "start_url": result},
                errback=self.handle_error,
            )

    def parse_site(self, response):
        """Parse individual site for contacts, follow internal links."""
        current_depth = response.meta.get("depth", 0)
        start_url = response.meta.get("start_url", response.url)
        domain = urlparse(response.url).netloc

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

        name = (
            response.css("h1::text").get("")
            or response.css("title::text").get("")
        ).strip()

        for email in emails:
            yield {
                "email": email,
                "name": name[:255] if name else None,
                "phone": None,
                "website": start_url,
                "address": None,
                "social_media": {},
                "source_type": "google_search",
                "source_url": response.url,
                "domain": domain,
                "keywords": self.query,
                "country": self.country,
                "job_id": self.job_id,
            }

    def handle_error(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url} - {failure.value}")
