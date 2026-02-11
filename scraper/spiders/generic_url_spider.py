"""
Generic URL Spider - Scrapes a list of provided URLs.
Extracts emails, phone numbers, names, and social media links.
"""

import re
from urllib.parse import urljoin, urlparse

import scrapy


class GenericUrlSpider(scrapy.Spider):
    name = "generic_urls"

    # Email regex (excludes common non-personal addresses)
    EMAIL_RE = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )
    PHONE_RE = re.compile(
        r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}"
    )
    EMAIL_BLACKLIST = [
        "noreply@", "no-reply@", "donotreply@", "admin@", "webmaster@",
        "postmaster@", "hostmaster@", "info@example", "contact@example",
        "support@example", "test@", "spam@", "abuse@",
    ]
    CONTACT_PAGE_PATTERNS = [
        "contact", "about", "team", "equipe", "a-propos", "nous-contacter",
        "our-team", "staff", "avocats", "lawyers", "attorneys",
    ]

    def __init__(self, job_id=None, urls=None, scrape_depth=2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.urls = urls or []
        self.scrape_depth = int(scrape_depth)
        self.visited_domains = set()

    def start_requests(self):
        for url in self.urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={"depth": 0, "start_url": url},
                errback=self.handle_error,
            )

    def parse(self, response):
        current_depth = response.meta.get("depth", 0)
        start_url = response.meta.get("start_url", response.url)
        domain = urlparse(response.url).netloc

        # Extract contacts from this page
        yield from self._extract_contacts(response, start_url)

        # Follow internal links up to configured depth
        if current_depth < self.scrape_depth:
            for link in response.css("a::attr(href)").getall():
                full_url = urljoin(response.url, link)
                link_domain = urlparse(full_url).netloc

                # Stay on same domain
                if link_domain != domain:
                    continue

                # Prioritize contact-like pages
                link_lower = full_url.lower()
                is_contact_page = any(
                    p in link_lower for p in self.CONTACT_PAGE_PATTERNS
                )
                priority = 0 if is_contact_page else 1

                yield scrapy.Request(
                    full_url,
                    callback=self.parse,
                    meta={"depth": current_depth + 1, "start_url": start_url},
                    priority=priority,
                    dont_filter=False,
                    errback=self.handle_error,
                )

    def _extract_contacts(self, response, start_url):
        """Extract all contact info from a page."""
        text = response.text
        domain = urlparse(response.url).netloc

        # Extract emails
        emails = set(self.EMAIL_RE.findall(text))
        emails = {
            e.lower() for e in emails
            if not any(bl in e.lower() for bl in self.EMAIL_BLACKLIST)
            and not e.endswith((".png", ".jpg", ".gif", ".css", ".js"))
        }

        # Extract phones
        phones = set(self.PHONE_RE.findall(text))

        # Extract name from page title or h1
        name = (
            response.css("h1::text").get("")
            or response.css("title::text").get("")
        ).strip()

        # Extract social media
        social = {}
        for link in response.css("a::attr(href)").getall():
            link_lower = link.lower()
            if "facebook.com/" in link_lower:
                social["facebook"] = link
            elif "instagram.com/" in link_lower:
                social["instagram"] = link
            elif "linkedin.com/" in link_lower:
                social["linkedin"] = link
            elif "twitter.com/" in link_lower or "x.com/" in link_lower:
                social["twitter"] = link
            elif "youtube.com/" in link_lower:
                social["youtube"] = link

        # Yield one item per email found
        for email in emails:
            yield {
                "email": email,
                "name": name[:255] if name else None,
                "phone": list(phones)[0] if phones else None,
                "website": start_url,
                "address": None,
                "social_media": social,
                "source_type": "custom_urls",
                "source_url": response.url,
                "domain": domain,
                "job_id": self.job_id,
            }

    def handle_error(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url} - {failure.value}")
