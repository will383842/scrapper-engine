"""
Forum Spider - Scrapes expat forums (expat.com, internations.org, etc.).
Extracts active members, moderators, and admins with their profiles and contact info.

Target forums:
- expat.com
- internations.org
- expatforum.com
- toytown-germany.com
- french-property.com forums
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


class ForumSpider(scrapy.Spider):
    name = "forum"

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_RE = re.compile(
        r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}"
    )

    # Forum base URLs
    FORUM_CONFIGS = {
        "expat.com": {
            "base_url": "https://www.expat.com/forum",
            "member_list_pattern": "/forum/memberlist.php?mode=joined&order=DESC&start={offset}",
            "profile_pattern": "/forum/memberlist.php?mode=viewprofile&u={user_id}",
            "members_per_page": 25,
        },
        "internations.org": {
            "base_url": "https://www.internations.org",
            "member_list_pattern": "/community/members?page={page}",
            "profile_pattern": "/profile/{username}",
            "members_per_page": 20,
        },
        "expatforum.com": {
            "base_url": "https://www.expatforum.com",
            "member_list_pattern": "/members?type=members&page={page}",
            "profile_pattern": "/members/{username}",
            "members_per_page": 30,
        },
    }

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "RETRY_TIMES": 3,
    }

    def __init__(
        self,
        job_id=None,
        forum_name="expat.com",
        max_members=200,
        country=None,
        keywords=None,
        target_roles=None,  # "admin,moderator,member"
        resume="false",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.forum_name = forum_name
        self.max_members = int(max_members)
        self.country = country
        self.keywords = keywords
        self.members_scraped = 0
        self.contacts_found = 0
        self.resume = resume == "true"

        # Parse target roles
        if target_roles:
            self.target_roles = [r.strip().lower() for r in target_roles.split(",")]
        else:
            self.target_roles = ["admin", "moderator", "member"]

        # Get forum configuration
        self.forum_config = self.FORUM_CONFIGS.get(
            forum_name, self.FORUM_CONFIGS["expat.com"]
        )

    def start_requests(self):
        # Load checkpoint if resuming
        start_page = 0
        if self.resume and self.job_id:
            checkpoint = load_checkpoint(int(self.job_id))
            if checkpoint:
                start_page = checkpoint.get("last_page", 0)
                self.members_scraped = checkpoint.get("members_scraped", 0)
                self.contacts_found = checkpoint.get("contacts_found", 0)
                self.logger.info(
                    f"Resuming from page {start_page}, "
                    f"{self.members_scraped} members scraped"
                )

        # Calculate pages needed
        members_per_page = self.forum_config["members_per_page"]
        pages_needed = (self.max_members // members_per_page) + 1

        # Start scraping member list pages
        for page in range(start_page, pages_needed):
            url = self._build_member_list_url(page)
            yield scrapy.Request(
                url,
                callback=self.parse_member_list,
                meta={"page": page},
                dont_filter=True,
            )

    def _build_member_list_url(self, page):
        """Build member list URL for the forum."""
        base_url = self.forum_config["base_url"]
        pattern = self.forum_config["member_list_pattern"]

        if "{offset}" in pattern:
            # phpBB style (expat.com)
            offset = page * self.forum_config["members_per_page"]
            url = base_url + pattern.format(offset=offset)
        elif "{page}" in pattern:
            # Modern pagination
            url = base_url + pattern.format(page=page + 1)
        else:
            url = base_url + pattern

        return url

    def parse_member_list(self, response):
        """Parse forum member list page to extract member profile URLs."""
        page = response.meta["page"]

        # Different selectors for different forum types
        profile_links = []

        # Try phpBB style (expat.com, expatforum.com)
        profile_links.extend(
            response.css(
                'a[href*="memberlist.php?mode=viewprofile"]::attr(href), '
                'a[href*="/members/"]::attr(href)'
            ).getall()
        )

        # Try XenForo style
        profile_links.extend(
            response.css(
                'a.username[href*="/members/"]::attr(href)'
            ).getall()
        )

        # Try custom patterns
        profile_links.extend(
            response.css(
                'a[href*="/profile/"]::attr(href), '
                'a.member-link::attr(href)'
            ).getall()
        )

        # Clean and deduplicate
        member_urls = []
        seen = set()
        for link in profile_links:
            full_url = response.urljoin(link)
            if full_url not in seen:
                member_urls.append(full_url)
                seen.add(full_url)

        self.logger.info(
            f"Page {page}: Found {len(member_urls)} member profiles"
        )

        # Scrape each member profile
        for member_url in member_urls:
            if self.members_scraped >= self.max_members:
                self.logger.info(
                    f"Reached max_members limit ({self.max_members})"
                )
                return

            yield scrapy.Request(
                member_url,
                callback=self.parse_member_profile,
                meta={"member_url": member_url},
            )

        # Save checkpoint
        if self.job_id:
            checkpoint_data = {
                "last_page": page + 1,
                "members_scraped": self.members_scraped,
                "contacts_found": self.contacts_found,
            }
            save_checkpoint(int(self.job_id), checkpoint_data)
            update_progress(
                int(self.job_id),
                progress=min(
                    100,
                    int((self.members_scraped / self.max_members) * 100),
                ),
                pages_scraped=page + 1,
                contacts_extracted=self.contacts_found,
            )

    def parse_member_profile(self, response):
        """Parse individual forum member profile."""
        member_url = response.meta["member_url"]
        self.members_scraped += 1

        # Extract username
        username = None
        username_selectors = [
            'h1.username::text',
            'h2.member-name::text',
            'span.username::text',
            'div.page-title h1::text',
        ]
        for selector in username_selectors:
            username_text = response.css(selector).get()
            if username_text:
                username = username_text.strip()
                break

        # Extract member role (admin, moderator, member)
        role = "member"
        role_indicators = response.css(
            'span.rank::text, '
            'div.member-role::text, '
            'span.user-title::text, '
            'dd.member-group::text'
        ).getall()

        for indicator in role_indicators:
            indicator_lower = indicator.lower()
            if "admin" in indicator_lower:
                role = "admin"
                break
            elif "moderator" in indicator_lower or "mod" in indicator_lower:
                role = "moderator"
                break

        # Check if role matches target
        if role not in self.target_roles:
            self.logger.debug(f"Skipping {username}: role {role} not in target")
            return

        # Extract email (often hidden, but sometimes in profile)
        email = None
        email_links = response.css('a[href^="mailto:"]::attr(href)').getall()
        if email_links:
            email = email_links[0].replace("mailto:", "")

        # Try to find email in profile fields
        if not email:
            profile_text = " ".join(
                response.css(
                    'dl.profile-fields dd::text, '
                    'div.about-section::text, '
                    'div.member-info::text'
                ).getall()
            )
            email_matches = self.EMAIL_RE.findall(profile_text)
            if email_matches:
                email = email_matches[0]

        # Extract website
        website = None
        website_links = response.css(
            'a[rel="nofollow"][target="_blank"]::attr(href), '
            'dd.homepage a::attr(href)'
        ).getall()
        for link in website_links:
            if link and not any(
                x in link for x in ["facebook.com", "twitter.com", "instagram.com"]
            ):
                website = link
                break

        # Extract location
        location = None
        location_selectors = [
            'dd.location::text',
            'span.member-location::text',
            'div.location::text',
        ]
        for selector in location_selectors:
            location_text = response.css(selector).get()
            if location_text:
                location = location_text.strip()
                break

        # Extract social media links
        social_media = {}
        facebook_link = response.css('a[href*="facebook.com"]::attr(href)').get()
        if facebook_link:
            social_media["facebook"] = facebook_link

        twitter_link = response.css('a[href*="twitter.com"]::attr(href)').get()
        if twitter_link:
            social_media["twitter"] = twitter_link

        instagram_link = response.css('a[href*="instagram.com"]::attr(href)').get()
        if instagram_link:
            social_media["instagram"] = instagram_link

        # Extract bio/about
        bio_text = " ".join(
            response.css(
                'div.about-content::text, '
                'div.signature::text, '
                'div.bio::text'
            ).getall()
        )

        # Create contact item if we have useful data
        if username and (email or website or bio_text):
            item = ContactItem()
            item["email"] = email
            item["name"] = username
            item["phone"] = None
            item["website"] = website or member_url
            item["address"] = location
            item["social_media"] = social_media
            item["source_type"] = "forum"
            item["source_url"] = member_url
            item["domain"] = (
                urlparse(website).netloc if website else self.forum_name
            )
            item["country"] = self.country
            item["keywords"] = " ".join(
                filter(
                    None,
                    [
                        self.keywords,
                        self.forum_name,
                        role,
                        "admin_groupe" if role == "admin" else None,
                    ],
                )
            )
            item["job_id"] = int(self.job_id) if self.job_id else None

            if email:
                self.contacts_found += 1

            self.logger.info(
                f"Member: {username} ({role}) | Email: {email or 'N/A'} | "
                f"Website: {website or 'N/A'}"
            )
            yield item

    def closed(self, reason):
        """Called when spider closes."""
        self.logger.info(
            f"Forum spider closed: {reason}\n"
            f"Members scraped: {self.members_scraped}\n"
            f"Contacts with email: {self.contacts_found}"
        )
