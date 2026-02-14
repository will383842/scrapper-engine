"""
Backlink Engine Pipeline - Send prospects to backlink-engine
"""

import logging
from typing import List, Dict
import asyncio

from scraper.items import ArticleItem
from scraper.integrations.backlink_engine_client import BacklinkEngineClient

logger = logging.getLogger(__name__)


class BacklinkEnginePipeline:
    """
    Pipeline to batch send prospects to backlink-engine.

    This runs AFTER PostgresPipeline and sends validated contacts
    to backlink-engine for automatic enrollment in outreach campaigns.
    """

    def __init__(self):
        self.client = BacklinkEngineClient()
        self.batch: List[Dict] = []
        self.batch_size = self.client.batch_size

    def open_spider(self, spider):
        """Initialize pipeline."""
        if self.client.is_enabled():
            logger.info("BacklinkEnginePipeline enabled - will send prospects to backlink-engine")
        else:
            logger.info("BacklinkEnginePipeline disabled (check BACKLINK_ENGINE_ENABLED env var)")

    def process_item(self, item, spider):
        """Process item and add to batch."""
        # Skip articles
        if isinstance(item, ArticleItem):
            return item

        # Skip if client is disabled
        if not self.client.is_enabled():
            return item

        # Convert Scrapy item to backlink-engine format
        prospect_data = self.client.format_prospect_from_scrapy_item(dict(item))

        # Add to batch
        self.batch.append(prospect_data)

        # Send batch if full
        if len(self.batch) >= self.batch_size:
            asyncio.run(self._send_batch())

        return item

    def close_spider(self, spider):
        """Send remaining batch on spider close."""
        if self.batch and self.client.is_enabled():
            logger.info(f"Sending final batch of {len(self.batch)} prospects to backlink-engine")
            asyncio.run(self._send_batch())

    async def _send_batch(self):
        """Send current batch to backlink-engine."""
        if not self.batch:
            return

        logger.info(f"Sending batch of {len(self.batch)} prospects to backlink-engine")

        try:
            result = await self.client.send_prospects(self.batch)
            if result:
                logger.info(
                    f"Backlink-engine batch sent: {result.get('created', 0)} created, "
                    f"{result.get('duplicates', 0)} duplicates, {result.get('errors', 0)} errors"
                )
        except Exception as e:
            logger.error(f"Failed to send batch to backlink-engine: {e}")
        finally:
            # Clear batch even on error to avoid re-sending same prospects
            self.batch = []
