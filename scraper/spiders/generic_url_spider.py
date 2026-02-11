"""
Generic URL Spider - Scrapes a list of provided URLs.
Extracts emails, phone numbers, names, and social media links.
Supports checkpoint/resume for interrupted jobs.
"""

import json
import re
from urllib.parse import urljoin, urlparse

import scrapy

from scraper.items import ContactItem
from scraper.utils.checkpoint import (
    get_completed_urls_for_job,
    load_checkpoint,
    mark_url_seen,
    save_checkpoint,
    update_progress,
)


class GenericUrlSpider(scrapy.Spider):
    name = "generic_urls"

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
    SOCIAL_PATTERNS = {
        "facebook": "facebook.com/",
        "instagram": "instagram.com/",
        "linkedin": "linkedin.com/",
        "twitter": ("twitter.com/", "x.com/"),
        "youtube": "youtube.com/",
    }

    def __init__(
        self, job_id=None, urls=None, scrape_depth=2,
        country=None, keywords=None, resume="false", *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.country = country
        self.keywords = keywords
        if isinstance(urls, str):
            try:
                self.urls = json.loads(urls)
            except (json.JSONDecodeError, TypeError):
                self.urls = [urls] if urls.startswith("http") else []
        else:
            self.urls = urls or []
        self.scrape_depth = int(scrape_depth)
        self.contacts_found = 0
        self.urls_completed = 0
        self.resume = resume == "true"

    def start_requests(self):
        # On resume, skip URLs already completed
        skip_urls = set()
        if self.resume and self.job_id:
            checkpoint = load_checkpoint(int(self.job_id))
            if checkpoint:
                self.contacts_found = checkpoint.get("contacts_found", 0)
                self.urls_completed = checkpoint.get("urls_completed", 0)
            # Also check which source URLs already have contacts in DB
            skip_urls = get_completed_urls_for_job(int(self.job_id))
            if skip_urls:
                self.logger.info(f"Resuming: skipping {len(skip_urls)} already-scraped URLs")

        for i, url in enumerate(self.urls):
            if url in skip_urls:
                continue
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={"depth": 0, "start_url": url, "url_index": i},
                errback=self.handle_error,
            )

    def parse(self, response):
        current_depth = response.meta.get("depth", 0)
        start_url = response.meta.get("start_url", response.url)
        url_index = response.meta.get("url_index", 0)
        domain = urlparse(response.url).netloc

        mark_url_seen(response.url, spider_name=self.name)
        yield from self._extract_contacts(response, start_url)

        # Save checkpoint after each root URL is processed
        if current_depth == 0 and self.job_id:
            self.urls_completed += 1
            total = len(self.urls)
            progress = self.urls_completed / total * 100 if total > 0 else 0
            save_checkpoint(int(self.job_id), {
                "urls_completed": self.urls_completed,
                "current_index": url_index,
                "contacts_found": self.contacts_found,
            })
            update_progress(
                int(self.job_id), progress,
                pages=self.urls_completed,
                contacts=self.contacts_found,
            )

        if current_depth < self.scrape_depth:
            for link in response.css("a::attr(href)").getall():
                full_url = urljoin(response.url, link)
                link_domain = urlparse(full_url).netloc
                if link_domain != domain:
                    continue

                link_lower = full_url.lower()
                is_contact_page = any(
                    p in link_lower for p in self.CONTACT_PAGE_PATTERNS
                )
                yield scrapy.Request(
                    full_url,
                    callback=self.parse,
                    meta={
                        "depth": current_depth + 1,
                        "start_url": start_url,
                        "url_index": url_index,
                    },
                    priority=0 if is_contact_page else 1,
                    dont_filter=False,
                    errback=self.handle_error,
                )

    def _extract_contacts(self, response, start_url):
        """Extract all contact info from a page."""
        text = response.text
        domain = urlparse(response.url).netloc

        emails = set(self.EMAIL_RE.findall(text))
        emails = {
            e.lower() for e in emails
            if not any(bl in e.lower() for bl in self.EMAIL_BLACKLIST)
            and not e.endswith((".png", ".jpg", ".gif", ".css", ".js"))
        }

        # Extract ALL phones (fixed: was only taking first)
        phones = list(set(self.PHONE_RE.findall(text)))

        name = (
            response.css("h1::text").get("")
            or response.css("title::text").get("")
        ).strip()

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
                "phone": phones[0] if phones else None,
                "website": start_url,
                "address": None,
                "social_media": social,
                "source_type": "custom_urls",
                "source_url": response.url,
                "domain": domain,
                "country": self.country,
                "keywords": self.keywords,
                "job_id": self.job_id,
            })

    def handle_error(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url} - {failure.value}")
