"""
Instagram Spider - Scrapes Instagram profiles (travel bloggers, influencers).
Extracts username, bio, email, website, follower count, and engagement metrics.

IMPORTANT: Instagram has extremely strict anti-scraping measures.
- Requires residential proxies (mandatory)
- Rate limit: 1 request per 15-20 seconds
- Often requires login session
- Very high risk of account/IP ban

Alternative: Use Instagram Graph API for legitimate business access.
This spider is for educational purposes only.
"""

import json
import re
from urllib.parse import urljoin, urlparse

import scrapy

from scraper.items import ContactItem
from scraper.utils.checkpoint import (
    save_checkpoint,
    load_checkpoint,
    update_progress,
)


class InstagramSpider(scrapy.Spider):
    name = "instagram"

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    custom_settings = {
        "DOWNLOAD_DELAY": 18,  # 18 seconds (very conservative)
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "RETRY_TIMES": 2,
        "USER_AGENT": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        # Residential proxies mandatory
        "PROXY_MODE": "residential_only",
    }

    def __init__(
        self,
        job_id=None,
        usernames=None,
        search_hashtag=None,
        search_location=None,
        max_profiles=100,
        min_followers=1000,
        country=None,
        keywords=None,
        resume="false",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.search_hashtag = search_hashtag
        self.search_location = search_location
        self.max_profiles = int(max_profiles)
        self.min_followers = int(min_followers)
        self.country = country
        self.keywords = keywords
        self.profiles_scraped = 0
        self.contacts_found = 0
        self.resume = resume == "true"

        # Parse usernames list
        if usernames:
            if isinstance(usernames, str):
                try:
                    self.usernames = json.loads(usernames)
                except json.JSONDecodeError:
                    # Split by comma or newline
                    self.usernames = [
                        u.strip() for u in re.split(r'[,\n]', usernames) if u.strip()
                    ]
            else:
                self.usernames = usernames or []
        else:
            self.usernames = []

    def start_requests(self):
        # Load checkpoint if resuming
        start_index = 0
        if self.resume and self.job_id:
            checkpoint = load_checkpoint(int(self.job_id))
            if checkpoint:
                start_index = checkpoint.get("last_username_index", 0)
                self.profiles_scraped = checkpoint.get("profiles_scraped", 0)
                self.contacts_found = checkpoint.get("contacts_found", 0)
                self.logger.info(
                    f"Resuming from index {start_index}, "
                    f"{self.profiles_scraped} profiles scraped"
                )

        # If search by hashtag
        if self.search_hashtag:
            # Instagram hashtag explore: https://www.instagram.com/explore/tags/{hashtag}/
            hashtag_url = f"https://www.instagram.com/explore/tags/{self.search_hashtag.replace('#', '')}/"
            yield scrapy.Request(
                hashtag_url,
                callback=self.parse_hashtag_page,
                meta={"hashtag": self.search_hashtag},
            )

        # If direct username list provided
        for idx, username in enumerate(self.usernames[start_index:], start=start_index):
            if self.profiles_scraped >= self.max_profiles:
                break

            # Clean username (remove @ if present)
            username = username.strip().replace("@", "")
            profile_url = f"https://www.instagram.com/{username}/"

            yield scrapy.Request(
                profile_url,
                callback=self.parse_profile,
                meta={"username": username, "index": idx},
            )

    def parse_hashtag_page(self, response):
        """Parse Instagram hashtag page to find top posts and extract usernames."""
        # Instagram loads content dynamically via JavaScript
        # Need to parse JSON data from script tags

        # Try to extract JSON data
        json_data = response.css(
            'script[type="application/ld+json"]::text'
        ).get()

        if json_data:
            try:
                data = json.loads(json_data)
                # Extract usernames from posts (structure varies)
                # This is a simplified example
                self.logger.info(f"Found JSON data: {len(json_data)} chars")
            except json.JSONDecodeError:
                pass

        # Fallback: try to extract profile links from HTML
        profile_links = response.css(
            'a[href^="/"][href$="/"]::attr(href)'
        ).getall()

        usernames = []
        for link in profile_links:
            # Extract username from /username/ format
            username = link.strip("/")
            if username and username not in ["explore", "accounts", "p"]:
                usernames.append(username)

        self.logger.info(
            f"Hashtag #{response.meta['hashtag']}: Found {len(usernames)} profiles"
        )

        # Scrape profiles
        for username in usernames[:self.max_profiles]:
            profile_url = f"https://www.instagram.com/{username}/"
            yield scrapy.Request(
                profile_url,
                callback=self.parse_profile,
                meta={"username": username},
            )

    def parse_profile(self, response):
        """Parse individual Instagram profile."""
        username = response.meta["username"]
        self.profiles_scraped += 1

        # Instagram embeds profile data in script tags as JSON
        # Look for window._sharedData or similar

        # Try to extract JSON data from script tags
        scripts = response.css('script:not([src])::text').getall()

        profile_data = None
        for script in scripts:
            if "window._sharedData" in script or "graphql" in script:
                # Try to parse JSON
                # This is complex as the structure varies
                try:
                    # Extract JSON object
                    json_match = re.search(r'\{.*"graphql".*\}', script, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(0))
                        # Navigate to user data (structure varies)
                        if "entry_data" in data:
                            profile_page = data.get("entry_data", {}).get("ProfilePage", [])
                            if profile_page:
                                profile_data = profile_page[0].get("graphql", {}).get("user", {})
                        elif "graphql" in data:
                            profile_data = data.get("graphql", {}).get("user", {})
                        break
                except (json.JSONDecodeError, IndexError):
                    continue

        # Extract data from JSON or HTML fallback
        if profile_data:
            # From JSON
            full_name = profile_data.get("full_name", "")
            bio = profile_data.get("biography", "")
            website = profile_data.get("external_url", "")
            followers = profile_data.get("edge_followed_by", {}).get("count", 0)
            following = profile_data.get("edge_follow", {}).get("count", 0)
            posts_count = profile_data.get("edge_owner_to_timeline_media", {}).get("count", 0)
            is_verified = profile_data.get("is_verified", False)
        else:
            # Fallback to HTML parsing (less reliable)
            full_name = response.css(
                'meta[property="og:title"]::attr(content)'
            ).get() or username
            bio = response.css(
                'meta[property="og:description"]::attr(content)'
            ).get() or ""
            website = response.css(
                'a[href][target="_blank"][rel*="nofollow"]::attr(href)'
            ).get()
            followers = 0
            following = 0
            posts_count = 0
            is_verified = False

        # Check minimum followers threshold
        if followers < self.min_followers:
            self.logger.debug(
                f"Skipping {username}: only {followers} followers "
                f"(min: {self.min_followers})"
            )
            return

        # Extract email from bio
        email = None
        email_matches = self.EMAIL_RE.findall(bio)
        if email_matches:
            # Take first email found
            email = email_matches[0]

        # Calculate engagement rate (if we have posts data)
        engagement_rate = 0
        if posts_count > 0 and followers > 0:
            # Simplified: would need actual likes/comments data
            # engagement_rate = (avg_likes + avg_comments) / followers * 100
            pass

        # Create contact item
        if username and (email or website or followers >= self.min_followers):
            item = ContactItem()
            item["email"] = email
            item["name"] = full_name or username
            item["phone"] = None
            item["website"] = website or f"https://www.instagram.com/{username}/"
            item["address"] = None
            item["social_media"] = {
                "instagram": f"https://www.instagram.com/{username}/",
                "followers": followers,
                "following": following,
                "posts": posts_count,
                "verified": is_verified,
            }
            item["source_type"] = "instagram"
            item["source_url"] = f"https://www.instagram.com/{username}/"
            item["domain"] = (
                urlparse(website).netloc if website else "instagram.com"
            )
            item["country"] = self.country
            item["keywords"] = " ".join(
                filter(
                    None,
                    [
                        self.keywords,
                        "influenceur" if followers >= 10000 else "blogueur",
                        self.search_hashtag,
                        bio[:50] if bio else None,
                    ],
                )
            )
            item["job_id"] = int(self.job_id) if self.job_id else None

            if email:
                self.contacts_found += 1

            self.logger.info(
                f"Profile: @{username} | Followers: {followers:,} | "
                f"Email: {email or 'N/A'} | Website: {website or 'N/A'}"
            )
            yield item

        # Save checkpoint
        if self.job_id and "index" in response.meta:
            checkpoint_data = {
                "last_username_index": response.meta["index"] + 1,
                "profiles_scraped": self.profiles_scraped,
                "contacts_found": self.contacts_found,
            }
            save_checkpoint(int(self.job_id), checkpoint_data)
            update_progress(
                int(self.job_id),
                progress=min(
                    100,
                    int((self.profiles_scraped / self.max_profiles) * 100),
                ),
                pages_scraped=self.profiles_scraped,
                contacts_extracted=self.contacts_found,
            )

    def closed(self, reason):
        """Called when spider closes."""
        self.logger.info(
            f"Instagram spider closed: {reason}\n"
            f"Profiles scraped: {self.profiles_scraped}\n"
            f"Contacts with email: {self.contacts_found}"
        )
