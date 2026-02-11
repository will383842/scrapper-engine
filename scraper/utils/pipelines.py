"""Scrapy pipelines for deduplication, validation, and DB storage."""

import hashlib
import json
import logging
import os

import redis

from scraper.database import get_db_session

logger = logging.getLogger(__name__)


class DeduplicationPipeline:
    """Drop duplicate contacts using Redis set + email uniqueness."""

    def __init__(self):
        self.redis_client = None

    def open_spider(self, spider):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            db=0,
            decode_responses=True,
        )

    def process_item(self, item, spider):
        email = item.get("email", "").lower().strip()
        if not email:
            raise DropItem("No email found")

        # Check Redis set for this spider run
        cache_key = f"scraper:seen_emails:{spider.job_id or 'default'}"
        if self.redis_client.sismember(cache_key, email):
            raise DropItem(f"Duplicate email: {email}")

        # Add to set with 24h TTL
        self.redis_client.sadd(cache_key, email)
        self.redis_client.expire(cache_key, 86400)

        return item


class ValidationPipeline:
    """Basic format validation before storing."""

    def process_item(self, item, spider):
        email = item.get("email", "").lower().strip()

        # Basic format check
        if "@" not in email or "." not in email.split("@")[-1]:
            raise DropItem(f"Invalid email format: {email}")

        # Normalize
        item["email"] = email
        if item.get("name"):
            item["name"] = item["name"].strip()[:255]

        return item


class PostgresPipeline:
    """Store scraped contacts in PostgreSQL."""

    def process_item(self, item, spider):
        with get_db_session() as session:
            session.execute(
                """
                INSERT INTO scraped_contacts
                    (email, name, phone, website, address, social_media,
                     source_type, source_url, domain, country, keywords,
                     job_id, status)
                VALUES
                    (:email, :name, :phone, :website, :address,
                     :social_media, :source_type, :source_url, :domain,
                     :country, :keywords, :job_id, 'pending_validation')
                ON CONFLICT DO NOTHING
                """,
                {
                    "email": item["email"],
                    "name": item.get("name"),
                    "phone": item.get("phone"),
                    "website": item.get("website"),
                    "address": item.get("address"),
                    "social_media": json.dumps(item.get("social_media", {})),
                    "source_type": item.get("source_type"),
                    "source_url": item.get("source_url"),
                    "domain": item.get("domain"),
                    "country": item.get("country"),
                    "keywords": item.get("keywords"),
                    "job_id": item.get("job_id"),
                },
            )

        logger.debug(f"Stored contact: {item['email']}")
        return item


class DropItem(Exception):
    """Raised to drop an item from the pipeline."""
    pass
