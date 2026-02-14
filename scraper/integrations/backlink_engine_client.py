"""
Backlink Engine Client - Send prospects to backlink-engine via webhook
"""

import os
import logging
from typing import List, Dict, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class BacklinkEngineClient:
    """Client for sending prospects to backlink-engine."""

    def __init__(self):
        self.enabled = os.getenv("BACKLINK_ENGINE_ENABLED", "false").lower() == "true"
        self.api_url = os.getenv("BACKLINK_ENGINE_API_URL")
        self.api_key = os.getenv("BACKLINK_ENGINE_API_KEY")
        self.batch_size = int(os.getenv("BACKLINK_ENGINE_BATCH_SIZE", "50"))
        self.timeout = int(os.getenv("BACKLINK_ENGINE_TIMEOUT", "30"))

        if self.enabled and not self.api_url:
            logger.warning(
                "BACKLINK_ENGINE_ENABLED=true but BACKLINK_ENGINE_API_URL not set"
            )
            self.enabled = False

        if self.enabled and not self.api_key:
            logger.warning(
                "BACKLINK_ENGINE_ENABLED=true but BACKLINK_ENGINE_API_KEY not set"
            )
            self.enabled = False

    def is_enabled(self) -> bool:
        """Check if backlink-engine integration is enabled."""
        return self.enabled

    async def send_prospect(self, prospect_data: Dict) -> Optional[Dict]:
        """
        Send a single prospect to backlink-engine.

        Args:
            prospect_data: Dict with keys:
                - domain (required): string
                - email (optional): string
                - name (optional): string
                - language (optional): string (ISO 639-1)
                - country (optional): string (ISO 3166-1 alpha-2)
                - category (optional): string (blogger, influencer, media, etc.)
                - source_url (optional): string

        Returns:
            Response dict from backlink-engine or None on failure
        """
        if not self.enabled:
            return None

        return await self.send_prospects([prospect_data])

    async def send_prospects(self, prospects: List[Dict]) -> Optional[Dict]:
        """
        Send multiple prospects to backlink-engine in batch.

        Args:
            prospects: List of prospect dicts (see send_prospect for format)

        Returns:
            Response dict with stats or None on failure
        """
        if not self.enabled:
            logger.debug("Backlink-engine integration disabled, skipping.")
            return None

        if not prospects:
            logger.debug("No prospects to send.")
            return None

        # Process in batches
        total_sent = 0
        total_duplicates = 0
        total_errors = 0

        for i in range(0, len(prospects), self.batch_size):
            batch = prospects[i : i + self.batch_size]

            try:
                result = await self._send_batch(batch)
                if result:
                    total_sent += result.get("created", 0)
                    total_duplicates += result.get("duplicates", 0)
                    total_errors += result.get("errors", 0)
            except Exception as e:
                logger.error(f"Failed to send batch: {e}")
                total_errors += len(batch)

        logger.info(
            f"Backlink-engine sync complete: {total_sent} created, "
            f"{total_duplicates} duplicates, {total_errors} errors"
        )

        return {
            "created": total_sent,
            "duplicates": total_duplicates,
            "errors": total_errors,
        }

    async def _send_batch(self, batch: List[Dict]) -> Optional[Dict]:
        """Send a single batch to backlink-engine API."""
        # Transform to backlink-engine format
        prospects = []
        for item in batch:
            prospect = {
                "domain": item.get("domain"),
                "category": item.get("category", "blogger"),
                "language": item.get("language"),
                "country": item.get("country"),
            }

            # Add contact if email is present
            if item.get("email"):
                prospect["contact"] = {
                    "email": item["email"],
                    "name": item.get("name"),
                }

            # Add source URL if present
            if item.get("source_url"):
                prospect["sourceUrl"] = item["source_url"]

            prospects.append(prospect)

        payload = {
            "prospects": prospects,
            "source": "scraper",
        }

        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"Batch sent successfully: {result.get('created', 0)} created, "
                        f"{result.get('duplicates', 0)} duplicates"
                    )
                    return result
                else:
                    logger.error(
                        f"Backlink-engine API error: {response.status_code} - {response.text}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("Backlink-engine API timeout")
            return None
        except Exception as e:
            logger.error(f"Backlink-engine API request failed: {e}")
            return None

    def format_prospect_from_scrapy_item(self, item: Dict) -> Dict:
        """
        Transform a Scrapy item into backlink-engine format.

        Args:
            item: Scrapy item dict from blog spider

        Returns:
            Formatted prospect dict
        """
        # Extract domain from URL
        domain = item.get("domain")
        if not domain and item.get("url"):
            # Parse domain from URL if not provided
            from urllib.parse import urlparse

            parsed = urlparse(item["url"])
            domain = parsed.netloc.replace("www.", "")

        return {
            "domain": domain,
            "email": item.get("email"),
            "name": item.get("name") or item.get("author"),
            "language": item.get("language"),
            "country": item.get("country"),
            "category": self._map_category(item.get("category")),
            "source_url": item.get("url"),
        }

    def _map_category(self, scraper_category: Optional[str]) -> str:
        """Map scraper category to backlink-engine category enum."""
        if not scraper_category:
            return "blogger"

        # Mapping table
        mapping = {
            "blog": "blogger",
            "blogger": "blogger",
            "influencer": "influencer",
            "news": "media",
            "media": "media",
            "magazine": "media",
            "association": "association",
            "ngo": "association",
            "partner": "partner",
            "agency": "agency",
            "corporate": "corporate",
            "ecommerce": "ecommerce",
        }

        return mapping.get(scraper_category.lower(), "blogger")
