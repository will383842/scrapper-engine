"""
YouTube Spider - Scrapes YouTube channels (travel vloggers, expat channels).
Extracts channel name, email (from About section), subscriber count, and links.

IMPORTANT: YouTube provides an official API (YouTube Data API v3).
Using the API is the recommended and legitimate way to access channel data.

This spider scrapes the public About page as a fallback.
Rate limiting and residential proxies recommended.
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


class YouTubeSpider(scrapy.Spider):
    name = "youtube"

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    custom_settings = {
        "DOWNLOAD_DELAY": 5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "RETRY_TIMES": 3,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    def __init__(
        self,
        job_id=None,
        channel_urls=None,
        channel_ids=None,
        search_query=None,
        max_channels=100,
        min_subscribers=5000,
        country=None,
        keywords=None,
        resume="false",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.search_query = search_query
        self.max_channels = int(max_channels)
        self.min_subscribers = int(min_subscribers)
        self.country = country
        self.keywords = keywords
        self.channels_scraped = 0
        self.contacts_found = 0
        self.resume = resume == "true"

        # Parse channel URLs
        if channel_urls:
            if isinstance(channel_urls, str):
                try:
                    self.channel_urls = json.loads(channel_urls)
                except json.JSONDecodeError:
                    self.channel_urls = [
                        u.strip() for u in channel_urls.split('\n') if u.strip()
                    ]
            else:
                self.channel_urls = channel_urls or []
        else:
            self.channel_urls = []

        # Parse channel IDs (UC... format)
        if channel_ids:
            if isinstance(channel_ids, str):
                try:
                    self.channel_ids = json.loads(channel_ids)
                except json.JSONDecodeError:
                    self.channel_ids = [
                        c.strip() for c in channel_ids.split(',') if c.strip()
                    ]
            else:
                self.channel_ids = channel_ids or []
        else:
            self.channel_ids = []

    def start_requests(self):
        # Load checkpoint if resuming
        start_index = 0
        if self.resume and self.job_id:
            checkpoint = load_checkpoint(int(self.job_id))
            if checkpoint:
                start_index = checkpoint.get("last_channel_index", 0)
                self.channels_scraped = checkpoint.get("channels_scraped", 0)
                self.contacts_found = checkpoint.get("contacts_found", 0)
                self.logger.info(
                    f"Resuming from index {start_index}, "
                    f"{self.channels_scraped} channels scraped"
                )

        # If search query provided, use YouTube search
        if self.search_query:
            # YouTube search: https://www.youtube.com/results?search_query=travel+vlog
            search_url = f"https://www.youtube.com/results?search_query={self.search_query.replace(' ', '+')}&sp=EgIQAg%253D%253D"  # sp param filters for channels
            yield scrapy.Request(
                search_url,
                callback=self.parse_search_results,
                meta={"page": 0},
            )

        # If channel URLs provided
        for idx, channel_url in enumerate(self.channel_urls[start_index:], start=start_index):
            if self.channels_scraped >= self.max_channels:
                break

            # Normalize URL to /about page
            about_url = self._get_about_url(channel_url)

            yield scrapy.Request(
                about_url,
                callback=self.parse_channel_about,
                meta={"channel_url": channel_url, "index": idx},
            )

        # If channel IDs provided
        for idx, channel_id in enumerate(self.channel_ids[start_index:], start=start_index):
            if self.channels_scraped >= self.max_channels:
                break

            about_url = f"https://www.youtube.com/channel/{channel_id}/about"

            yield scrapy.Request(
                about_url,
                callback=self.parse_channel_about,
                meta={"channel_id": channel_id, "index": idx},
            )

    def _get_about_url(self, channel_url):
        """Convert any YouTube channel URL to its /about page."""
        if "/about" in channel_url:
            return channel_url
        elif "/channel/" in channel_url:
            return channel_url.rstrip("/") + "/about"
        elif "/c/" in channel_url or "/@" in channel_url:
            return channel_url.rstrip("/") + "/about"
        else:
            return channel_url + "/about"

    def parse_search_results(self, response):
        """Parse YouTube search results to extract channel URLs."""
        # YouTube loads search results dynamically
        # Need to parse JSON from script tags

        scripts = response.css('script::text').getall()

        channel_urls = []
        for script in scripts:
            if "var ytInitialData" in script:
                # Extract JSON
                json_match = re.search(r'var ytInitialData = (\{.*?\});', script, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        # Navigate through complex JSON structure
                        # This is simplified - actual structure is very nested
                        contents = (
                            data.get("contents", {})
                            .get("twoColumnSearchResultsRenderer", {})
                            .get("primaryContents", {})
                            .get("sectionListRenderer", {})
                            .get("contents", [])
                        )

                        for content in contents:
                            item_section = content.get("itemSectionRenderer", {})
                            for item in item_section.get("contents", []):
                                channel_renderer = item.get("channelRenderer", {})
                                if channel_renderer:
                                    channel_id = channel_renderer.get("channelId")
                                    if channel_id:
                                        channel_urls.append(
                                            f"https://www.youtube.com/channel/{channel_id}/about"
                                        )
                        break
                    except (json.JSONDecodeError, KeyError):
                        continue

        self.logger.info(
            f"Search '{self.search_query}': Found {len(channel_urls)} channels"
        )

        # Scrape each channel
        for about_url in channel_urls[:self.max_channels]:
            yield scrapy.Request(
                about_url,
                callback=self.parse_channel_about,
                meta={"channel_url": about_url},
            )

    def parse_channel_about(self, response):
        """Parse YouTube channel About page."""
        self.channels_scraped += 1

        # Extract data from JSON in script tags
        scripts = response.css('script::text').getall()

        channel_data = None
        for script in scripts:
            if "var ytInitialData" in script:
                json_match = re.search(r'var ytInitialData = (\{.*?\});', script, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        # Navigate to channel metadata
                        # Structure: data > header > c4TabbedHeaderRenderer or channelHeaderRenderer
                        header = data.get("header", {})
                        channel_renderer = (
                            header.get("c4TabbedHeaderRenderer") or
                            header.get("pageHeaderRenderer")
                        )

                        # About tab content
                        about_content = (
                            data.get("contents", {})
                            .get("twoColumnBrowseResultsRenderer", {})
                            .get("tabs", [])
                        )

                        # Find about tab
                        for tab in about_content:
                            tab_renderer = tab.get("tabRenderer", {})
                            if tab_renderer.get("title") == "About":
                                channel_data = (
                                    tab_renderer
                                    .get("content", {})
                                    .get("sectionListRenderer", {})
                                    .get("contents", [{}])[0]
                                    .get("itemSectionRenderer", {})
                                    .get("contents", [{}])[0]
                                    .get("channelAboutFullMetadataRenderer", {})
                                )
                                break

                        if channel_data:
                            break
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        if not channel_data:
            self.logger.warning(f"Could not extract channel data from {response.url}")
            return

        # Extract channel information
        channel_name = channel_data.get("title", {}).get("simpleText", "")
        channel_id = channel_data.get("channelId", "")
        description = channel_data.get("description", {}).get("simpleText", "")

        # Subscriber count
        subscriber_text = (
            channel_data.get("subscriberCountText", {}).get("simpleText", "")
        )
        subscribers = self._parse_subscriber_count(subscriber_text)

        # Check minimum subscribers threshold
        if subscribers < self.min_subscribers:
            self.logger.debug(
                f"Skipping {channel_name}: only {subscribers:,} subscribers "
                f"(min: {self.min_subscribers:,})"
            )
            return

        # Extract email from description
        email = None
        email_matches = self.EMAIL_RE.findall(description)
        if email_matches:
            # Filter out likely non-business emails
            for em in email_matches:
                if not any(
                    bad in em.lower()
                    for bad in ["youtube.com", "gmail.com", "noreply"]
                ):
                    email = em
                    break
            # If no business email, accept gmail as fallback
            if not email and email_matches:
                email = email_matches[0]

        # Extract primary links
        links = channel_data.get("primaryLinks", [])
        website = None
        social_media = {}

        for link in links:
            url = link.get("navigationEndpoint", {}).get("urlEndpoint", {}).get("url", "")
            title = link.get("title", {}).get("simpleText", "")

            if url:
                # Check if it's a social media link or website
                if "instagram.com" in url:
                    social_media["instagram"] = url
                elif "facebook.com" in url:
                    social_media["facebook"] = url
                elif "twitter.com" in url or "x.com" in url:
                    social_media["twitter"] = url
                elif not website and "youtube.com" not in url:
                    # First non-YouTube link is likely the main website
                    website = url

        # Country
        channel_country = channel_data.get("country", {}).get("simpleText", "")

        # View count
        view_count_text = (
            channel_data.get("viewCountText", {}).get("simpleText", "")
        )
        views = self._parse_view_count(view_count_text)

        # Create contact item
        if channel_name and (email or website or subscribers >= self.min_subscribers):
            channel_url = f"https://www.youtube.com/channel/{channel_id}" if channel_id else response.url

            item = ContactItem()
            item["email"] = email
            item["name"] = channel_name
            item["phone"] = None
            item["website"] = website or channel_url
            item["address"] = channel_country
            item["social_media"] = {
                "youtube": channel_url,
                "subscribers": subscribers,
                "views": views,
                **social_media,
            }
            item["source_type"] = "youtube"
            item["source_url"] = channel_url
            item["domain"] = (
                urlparse(website).netloc if website else "youtube.com"
            )
            item["country"] = self.country or channel_country
            item["keywords"] = " ".join(
                filter(
                    None,
                    [
                        self.keywords,
                        "youtubeur",
                        self.search_query,
                        description[:50] if description else None,
                    ],
                )
            )
            item["job_id"] = int(self.job_id) if self.job_id else None

            if email:
                self.contacts_found += 1

            self.logger.info(
                f"Channel: {channel_name} | Subscribers: {subscribers:,} | "
                f"Email: {email or 'N/A'} | Website: {website or 'N/A'}"
            )
            yield item

        # Save checkpoint
        if self.job_id and "index" in response.meta:
            checkpoint_data = {
                "last_channel_index": response.meta["index"] + 1,
                "channels_scraped": self.channels_scraped,
                "contacts_found": self.contacts_found,
            }
            save_checkpoint(int(self.job_id), checkpoint_data)
            update_progress(
                int(self.job_id),
                progress=min(
                    100,
                    int((self.channels_scraped / self.max_channels) * 100),
                ),
                pages_scraped=self.channels_scraped,
                contacts_extracted=self.contacts_found,
            )

    def _parse_subscriber_count(self, text):
        """Parse subscriber count text like '125K subscribers' to integer."""
        if not text:
            return 0

        text = text.lower().replace("subscribers", "").replace("subscriber", "").strip()

        multipliers = {"k": 1000, "m": 1000000, "b": 1000000000}

        for suffix, multiplier in multipliers.items():
            if suffix in text:
                try:
                    num = float(text.replace(suffix, "").strip())
                    return int(num * multiplier)
                except ValueError:
                    return 0

        # No suffix, try direct integer
        try:
            # Remove commas
            return int(text.replace(",", ""))
        except ValueError:
            return 0

    def _parse_view_count(self, text):
        """Parse view count text like '1.2M views' to integer."""
        if not text:
            return 0

        text = text.lower().replace("views", "").replace("view", "").strip()
        return self._parse_subscriber_count(text)

    def closed(self, reason):
        """Called when spider closes."""
        self.logger.info(
            f"YouTube spider closed: {reason}\n"
            f"Channels scraped: {self.channels_scraped}\n"
            f"Contacts with email: {self.contacts_found}"
        )
