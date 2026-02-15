"""
Facebook Spider - Scrapes Facebook business pages (law firms, insurance agencies).
Extracts page name, email, phone, website, address, and social links.

IMPORTANT: Facebook has very strict anti-scraping measures.
- Requires residential proxies
- Rate limit: 1 request per 10-15 seconds
- Often requires login (session cookies)
- High risk of account/IP ban

This spider is for educational purposes. Use responsibly and comply with Facebook ToS.
Alternative: Use Facebook Graph API for legitimate business data access.
"""

import json
import re
from urllib.parse import urljoin, urlparse, parse_qs

import scrapy

from scraper.items import ContactItem
from scraper.utils.checkpoint import (
    save_checkpoint,
    load_checkpoint,
    update_progress,
)


class FacebookSpider(scrapy.Spider):
    name = "facebook"

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_RE = re.compile(
        r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}"
    )

    custom_settings = {
        "DOWNLOAD_DELAY": 12,  # 12 seconds between requests (very conservative)
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "RETRY_TIMES": 2,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Residential proxies mandatory for Facebook
        "PROXY_MODE": "residential_only",
    }

    def __init__(
        self,
        job_id=None,
        page_urls=None,
        search_query=None,
        location=None,
        max_results=50,
        country=None,
        keywords=None,
        resume="false",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.search_query = search_query
        self.location = location
        self.max_results = int(max_results)
        self.country = country
        self.keywords = keywords
        self.pages_scraped = 0
        self.contacts_found = 0
        self.resume = resume == "true"

        # Parse page URLs
        if page_urls:
            if isinstance(page_urls, str):
                try:
                    self.page_urls = json.loads(page_urls)
                except json.JSONDecodeError:
                    self.page_urls = [page_urls] if page_urls.startswith("http") else []
            else:
                self.page_urls = page_urls or []
        else:
            self.page_urls = []

    def start_requests(self):
        # Load checkpoint if resuming
        start_index = 0
        if self.resume and self.job_id:
            checkpoint = load_checkpoint(int(self.job_id))
            if checkpoint:
                start_index = checkpoint.get("last_page_index", 0)
                self.pages_scraped = checkpoint.get("pages_scraped", 0)
                self.contacts_found = checkpoint.get("contacts_found", 0)
                self.logger.info(
                    f"Resuming from index {start_index}, "
                    f"{self.pages_scraped} pages scraped"
                )

        # If search query provided, use Facebook search
        if self.search_query:
            # Facebook search for pages: https://www.facebook.com/search/pages/?q=lawyer+bangkok
            search_url = f"https://www.facebook.com/search/pages/?q={self.search_query.replace(' ', '+')}"
            yield scrapy.Request(
                search_url,
                callback=self.parse_search_results,
                meta={"page": 0},
            )

        # If direct page URLs provided, scrape them
        for idx, page_url in enumerate(self.page_urls[start_index:], start=start_index):
            if self.pages_scraped >= self.max_results:
                break

            # Ensure it's a full Facebook URL
            if not page_url.startswith("http"):
                page_url = f"https://www.facebook.com/{page_url}"

            yield scrapy.Request(
                page_url,
                callback=self.parse_page,
                meta={"page_url": page_url, "index": idx},
            )

    def parse_search_results(self, response):
        """Parse Facebook search results to extract page URLs."""
        # Facebook loads search results dynamically via JavaScript
        # This requires Selenium/Playwright or parsing JSON from script tags

        # Try to extract page links from HTML
        page_links = response.css(
            'a[href*="/pages/"]::attr(href), '
            'a[href^="https://www.facebook.com/"][href*="?"]::attr(href)'
        ).getall()

        # Clean and deduplicate
        page_urls = []
        seen = set()
        for link in page_links:
            # Extract clean page URL
            clean_url = link.split("?")[0]
            if clean_url not in seen and "/pages/" in clean_url:
                page_urls.append(clean_url)
                seen.add(clean_url)

        self.logger.info(f"Search results: Found {len(page_urls)} page URLs")

        # Scrape each page
        for page_url in page_urls[:self.max_results]:
            full_url = response.urljoin(page_url)
            yield scrapy.Request(
                full_url,
                callback=self.parse_page,
                meta={"page_url": full_url},
            )

    def parse_page(self, response):
        """Parse individual Facebook business page."""
        page_url = response.meta["page_url"]
        self.pages_scraped += 1

        # Extract page name
        name = None
        name_selectors = [
            'h1::text',
            'span.x1lliihq.x6ikm8r.x10wlt62::text',
            'meta[property="og:title"]::attr(content)',
        ]
        for selector in name_selectors:
            name_text = response.css(selector).get()
            if name_text:
                name = name_text.strip()
                break

        # Extract about/description
        about_text = " ".join(
            response.css(
                'div[data-testid="page_about_section"] span::text, '
                'div.x1ey2m1c span::text'
            ).getall()
        )

        # Extract email from about section or contact info
        email = None
        email_matches = self.EMAIL_RE.findall(about_text)
        if email_matches:
            for em in email_matches:
                if not any(
                    bad in em.lower()
                    for bad in ["facebook.com", "fb.com", "example.com"]
                ):
                    email = em
                    break

        # Try to find email in meta tags
        if not email:
            email_meta = response.css('meta[property="og:email"]::attr(content)').get()
            if email_meta:
                email = email_meta

        # Extract phone
        phone = None
        phone_matches = self.PHONE_RE.findall(about_text)
        if phone_matches:
            phone = phone_matches[0]

        # Try to find phone in specific sections
        if not phone:
            phone_text = response.css(
                'a[href^="tel:"]::attr(href), '
                'div[data-testid="page_contact_section"] span::text'
            ).get()
            if phone_text:
                if phone_text.startswith("tel:"):
                    phone = phone_text.replace("tel:", "")
                else:
                    phone_matches = self.PHONE_RE.findall(phone_text)
                    if phone_matches:
                        phone = phone_matches[0]

        # Extract website
        website = None
        website_links = response.css(
            'a[href*="l.facebook.com/l.php"]::attr(href), '
            'div[data-testid="page_contact_section"] a[target="_blank"]::attr(href)'
        ).getall()

        for link in website_links:
            # Facebook wraps external links in l.facebook.com/l.php?u=...
            if "l.facebook.com/l.php" in link:
                parsed = urlparse(link)
                params = parse_qs(parsed.query)
                if "u" in params:
                    website = params["u"][0]
                    break
            elif link and not link.startswith("https://www.facebook.com"):
                website = link
                break

        # Extract address/location
        address = None
        address_text = response.css(
            'div[data-testid="page_location"] span::text, '
            'span.x1lliihq.x6ikm8r.x10wlt62.x1n2onr6::text'
        ).get()
        if address_text:
            address = address_text.strip()

        # Extract category
        category_text = response.css(
            'meta[property="og:type"]::attr(content), '
            'span[class*="category"]::text'
        ).get()

        # Create contact item
        if name or email or phone:
            item = ContactItem()
            item["email"] = email
            item["name"] = name
            item["phone"] = phone
            item["website"] = website or page_url
            item["address"] = address
            item["social_media"] = {"facebook": page_url}
            item["source_type"] = "facebook"
            item["source_url"] = page_url
            item["domain"] = (
                urlparse(website).netloc if website else "facebook.com"
            )
            item["country"] = self.country
            item["keywords"] = " ".join(
                filter(
                    None,
                    [
                        self.keywords,
                        self.search_query,
                        category_text,
                        name,
                    ],
                )
            )
            item["job_id"] = int(self.job_id) if self.job_id else None

            if email:
                self.contacts_found += 1

            self.logger.info(
                f"Page: {name} | Email: {email or 'N/A'} | "
                f"Phone: {phone or 'N/A'}"
            )
            yield item

        # Save checkpoint
        if self.job_id and "index" in response.meta:
            checkpoint_data = {
                "last_page_index": response.meta["index"] + 1,
                "pages_scraped": self.pages_scraped,
                "contacts_found": self.contacts_found,
            }
            save_checkpoint(int(self.job_id), checkpoint_data)
            update_progress(
                int(self.job_id),
                progress=min(
                    100,
                    int((self.pages_scraped / max(self.max_results, 1)) * 100),
                ),
                pages_scraped=self.pages_scraped,
                contacts_extracted=self.contacts_found,
            )

    def closed(self, reason):
        """Called when spider closes."""
        self.logger.info(
            f"Facebook spider closed: {reason}\n"
            f"Pages scraped: {self.pages_scraped}\n"
            f"Contacts with email: {self.contacts_found}"
        )
