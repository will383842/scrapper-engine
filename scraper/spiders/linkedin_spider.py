"""
LinkedIn Spider - Scrapes LinkedIn profiles (lawyers, consultants, accountants).
Extracts name, email (if public), company, location, and profile URL.

IMPORTANT: LinkedIn has strict anti-scraping measures.
- Use residential proxies only
- Rate limit: 1 request per 5-10 seconds
- Requires authentication (optional session cookies)
- Risk of IP/account ban if detected

This spider is for educational purposes. Use responsibly and comply with LinkedIn ToS.
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


class LinkedInSpider(scrapy.Spider):
    name = "linkedin"

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    # LinkedIn search URL patterns
    # Example: https://www.linkedin.com/search/results/people/?keywords=lawyer%20bangkok
    LINKEDIN_SEARCH_BASE = "https://www.linkedin.com/search/results/people/"

    custom_settings = {
        "DOWNLOAD_DELAY": 8,  # 8 seconds between requests (conservative)
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "RETRY_TIMES": 3,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Use residential proxies for LinkedIn
        "PROXY_MODE": "residential_only",
    }

    def __init__(
        self,
        job_id=None,
        query=None,
        location=None,
        max_results=100,
        country=None,
        keywords=None,
        resume="false",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.query = query or "lawyer"
        self.location = location or ""
        self.max_results = int(max_results)
        self.country = country
        self.keywords = keywords
        self.profiles_scraped = 0
        self.contacts_found = 0
        self.resume = resume == "true"

    def start_requests(self):
        # Load checkpoint if resuming
        start_page = 0
        if self.resume and self.job_id:
            checkpoint = load_checkpoint(int(self.job_id))
            if checkpoint:
                start_page = checkpoint.get("last_page", 0)
                self.profiles_scraped = checkpoint.get("profiles_scraped", 0)
                self.contacts_found = checkpoint.get("contacts_found", 0)
                self.logger.info(
                    f"Resuming from page {start_page}, "
                    f"{self.profiles_scraped} profiles scraped"
                )

        # LinkedIn search with pagination
        # Note: LinkedIn limits search results (typically ~1000 results max)
        pages_needed = (self.max_results // 10) + 1

        for page in range(start_page, min(pages_needed, 100)):
            url = self._build_search_url(page)
            yield scrapy.Request(
                url,
                callback=self.parse_search_results,
                meta={"page": page},
                dont_filter=True,
            )

    def _build_search_url(self, page):
        """Build LinkedIn people search URL with pagination."""
        start = page * 10
        params = {
            "keywords": self.query,
            "origin": "GLOBAL_SEARCH_HEADER",
            "start": start,
        }
        if self.location:
            params["location"] = self.location

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.LINKEDIN_SEARCH_BASE}?{query_string}"

    def parse_search_results(self, response):
        """Parse LinkedIn search results page to extract profile URLs."""
        page = response.meta["page"]

        # LinkedIn search results are loaded dynamically via JavaScript
        # We need to parse the initial HTML or use Selenium/Playwright
        # For simplicity, this example uses CSS selectors for static HTML

        # Try to find profile links
        profile_links = response.css(
            'a.app-aware-link[href*="/in/"]::attr(href)'
        ).getall()

        if not profile_links:
            # Fallback: try alternate selectors
            profile_links = response.css(
                'a[href*="linkedin.com/in/"]::attr(href)'
            ).getall()

        # Clean and deduplicate URLs
        profile_urls = []
        seen = set()
        for link in profile_links:
            # Extract clean profile URL
            if "/in/" in link:
                # Remove query params
                clean_url = link.split("?")[0]
                if clean_url not in seen:
                    profile_urls.append(clean_url)
                    seen.add(clean_url)

        self.logger.info(
            f"Page {page}: Found {len(profile_urls)} profile URLs"
        )

        # Scrape each profile
        for profile_url in profile_urls:
            if self.profiles_scraped >= self.max_results:
                self.logger.info(
                    f"Reached max_results limit ({self.max_results})"
                )
                return

            full_url = response.urljoin(profile_url)
            yield scrapy.Request(
                full_url,
                callback=self.parse_profile,
                meta={"profile_url": full_url},
            )

        # Save checkpoint after each page
        if self.job_id:
            checkpoint_data = {
                "last_page": page + 1,
                "profiles_scraped": self.profiles_scraped,
                "contacts_found": self.contacts_found,
            }
            save_checkpoint(int(self.job_id), checkpoint_data)
            update_progress(
                int(self.job_id),
                progress=min(
                    100,
                    int((self.profiles_scraped / self.max_results) * 100),
                ),
                pages_scraped=page + 1,
                contacts_extracted=self.contacts_found,
            )

    def parse_profile(self, response):
        """Parse individual LinkedIn profile page."""
        profile_url = response.meta["profile_url"]
        self.profiles_scraped += 1

        # Extract name
        name = None
        name_selectors = [
            'h1.text-heading-xlarge::text',
            'h1[class*="pv-top-card"]::text',
            'div.pv-text-details__left-panel h1::text',
        ]
        for selector in name_selectors:
            name_text = response.css(selector).get()
            if name_text:
                name = name_text.strip()
                break

        # Extract headline/title
        headline = response.css(
            'div.text-body-medium::text, '
            'div[class*="pv-top-card"] div.text-body-medium::text'
        ).get()
        if headline:
            headline = headline.strip()

        # Extract company
        company = response.css(
            'button[aria-label*="Current company"] div.t-bold span::text, '
            'div[class*="pv-top-card"] button span.t-bold span::text'
        ).get()

        # Extract location
        location = response.css(
            'span.text-body-small.inline.t-black--light.break-words::text, '
            'div.pv-text-details__left-panel span.text-body-small::text'
        ).get()
        if location:
            location = location.strip()

        # Extract about section (may contain email)
        about_text = " ".join(
            response.css(
                'section[data-section="summary"] div.pv-shared-text-with-see-more span::text, '
                'div[class*="about"] span::text'
            ).getall()
        )

        # Try to extract email from about section or contact info
        email = None
        email_matches = self.EMAIL_RE.findall(about_text)
        if email_matches:
            # Filter out likely non-personal emails
            for em in email_matches:
                if not any(
                    bad in em.lower()
                    for bad in ["linkedin.com", "example.com", "noreply"]
                ):
                    email = em
                    break

        # Extract website/contact info button link
        website = None
        contact_links = response.css(
            'a[href*="contact-info"]::attr(href), '
            'section.pv-contact-info a::attr(href)'
        ).getall()
        for link in contact_links:
            if link and ("http://" in link or "https://" in link):
                if "linkedin.com" not in link:
                    website = link
                    break

        # If no email found and we have valuable data, still create item
        # (email can be enriched later via WHOIS or website scraping)
        if name or headline or company:
            item = ContactItem()
            item["email"] = email
            item["name"] = name
            item["phone"] = None
            item["website"] = website or profile_url
            item["address"] = location
            item["social_media"] = {"linkedin": profile_url}
            item["source_type"] = "linkedin"
            item["source_url"] = profile_url
            item["domain"] = (
                urlparse(website).netloc if website else "linkedin.com"
            )
            item["country"] = self.country
            item["keywords"] = " ".join(
                filter(
                    None,
                    [self.keywords, self.query, headline, company],
                )
            )
            item["job_id"] = int(self.job_id) if self.job_id else None

            if email:
                self.contacts_found += 1

            self.logger.info(
                f"Profile: {name} | {company} | Email: {email or 'N/A'}"
            )
            yield item

    def closed(self, reason):
        """Called when spider closes."""
        self.logger.info(
            f"LinkedIn spider closed: {reason}\n"
            f"Profiles scraped: {self.profiles_scraped}\n"
            f"Contacts with email: {self.contacts_found}"
        )
