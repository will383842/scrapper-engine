"""Scrapy pipelines for deduplication, validation, and DB storage."""

import hashlib
import json
import logging
import os

import redis
from scrapy.exceptions import DropItem

from scraper.database import get_db_session
from scraper.items import ArticleItem
from scraper.utils.checkpoint import is_url_seen, mark_url_seen
from scraper.utils.deduplication_pro import DeduplicationManager
from sqlalchemy import text

logger = logging.getLogger(__name__)


class UltraProDeduplicationPipeline:
    """
    ULTRA-PROFESSIONAL multi-layer deduplication pipeline.

    Layers:
    1. URL exact match
    2. URL normalized (http/https, www, trailing slash)
    3. Email deduplication
    4. Content hash (similar pages)
    5. Temporal (don't re-scrape if recent)

    This pipeline REPLACES the old DeduplicationPipeline.
    """

    def __init__(self):
        self.manager: DeduplicationManager = None

    def open_spider(self, spider):
        """Initialize deduplication manager for this spider."""
        job_id = getattr(spider, "job_id", None)
        self.manager = DeduplicationManager(job_id=job_id)
        logger.info(f"UltraProDeduplicationPipeline initialized for job #{job_id or 'default'}")

    def process_item(self, item, spider):
        """Process item through all deduplication layers."""
        # Skip articles (handled separately)
        if isinstance(item, ArticleItem):
            return item

        source_url = item.get("source_url", "")
        email = item.get("email", "").lower().strip()

        # Layer 1: URL exact match
        if source_url and self.manager.is_url_seen_exact(source_url):
            raise DropItem(f"URL already scraped (exact): {source_url}")

        # Layer 2: URL normalized
        if source_url and self.manager.is_url_seen_normalized(source_url):
            raise DropItem(f"URL already scraped (normalized): {source_url}")

        # Layer 3: Email deduplication
        if not email:
            raise DropItem("No email found")

        if self.manager.is_email_seen(email):
            raise DropItem(f"Email already scraped: {email}")

        # Layer 4: Content hash (if content available)
        content = item.get("content_text", "")
        if content:
            is_seen, content_hash = self.manager.is_content_seen(content)
            if is_seen:
                raise DropItem(f"Content already scraped (hash: {content_hash[:16]}...)")
            item["content_hash"] = content_hash

        # Layer 5: Temporal deduplication
        if source_url and self.manager.is_url_recently_scraped(source_url):
            raise DropItem(f"URL scraped recently: {source_url}")

        # Mark all as seen
        if source_url:
            self.manager.mark_url_seen_exact(source_url)
            self.manager.mark_url_seen_normalized(source_url)

        self.manager.mark_email_seen(email)

        if content and item.get("content_hash"):
            self.manager.mark_content_seen(item["content_hash"])

        return item

    def close_spider(self, spider):
        """Log deduplication statistics on spider close."""
        if self.manager:
            self.manager.log_stats()


class DeduplicationPipeline:
    """Drop duplicate contacts using Redis set + email uniqueness."""

    def __init__(self):
        self.redis_client = None

    def open_spider(self, spider):
        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                password=os.getenv("REDIS_PASSWORD"),
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable, dedup will use in-memory set: {e}")
            self.redis_client = None
            self._memory_set = set()

    def process_item(self, item, spider):
        if isinstance(item, ArticleItem):
            return item

        email = item.get("email", "").lower().strip()
        if not email:
            raise DropItem("No email found")

        if self.redis_client:
            try:
                cache_key = f"scraper:seen_emails:{spider.job_id or 'default'}"
                # Atomic check-and-add: sadd returns 0 if already exists, 1 if added
                added = self.redis_client.sadd(cache_key, email)
                if not added:
                    raise DropItem(f"Duplicate email: {email}")
                self.redis_client.expire(cache_key, 86400)
            except redis.ConnectionError:
                logger.warning("Redis connection lost, falling back to in-memory dedup")
                self.redis_client = None
                self._memory_set = set()
                if email in self._memory_set:
                    raise DropItem(f"Duplicate email: {email}")
                self._memory_set.add(email)
        else:
            if email in self._memory_set:
                raise DropItem(f"Duplicate email: {email}")
            self._memory_set.add(email)

        return item


class ValidationPipeline:
    """Basic format validation before storing."""

    def process_item(self, item, spider):
        if isinstance(item, ArticleItem):
            return item

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
        if isinstance(item, ArticleItem):
            return item

        with get_db_session() as session:
            session.execute(
                text("""
                INSERT INTO scraped_contacts
                    (email, name, phone, website, address, social_media,
                     source_type, source_url, domain, country, keywords,
                     job_id, status)
                VALUES
                    (:email, :name, :phone, :website, :address,
                     :social_media, :source_type, :source_url, :domain,
                     :country, :keywords, :job_id, 'pending_validation')
                ON CONFLICT (email) DO UPDATE SET
                    scraped_at = NOW(),
                    job_id = EXCLUDED.job_id
                """),
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


class ProgressTrackingPipeline:
    """Update job progress counters in DB after each stored contact."""

    def __init__(self):
        self._counts = {}  # job_id -> count

    def process_item(self, item, spider):
        if isinstance(item, ArticleItem):
            return item

        job_id = item.get("job_id")
        if not job_id:
            return item

        job_id = int(job_id)
        self._counts[job_id] = self._counts.get(job_id, 0) + 1

        # Update DB every 10 contacts to avoid excessive writes
        if self._counts[job_id] % 10 == 0:
            self._flush(job_id)

        return item

    def close_spider(self, spider):
        """Flush remaining counts on spider close."""
        for job_id, count in self._counts.items():
            self._flush(job_id)

    def _flush(self, job_id: int):
        try:
            with get_db_session() as session:
                session.execute(
                    text("""
                        UPDATE scraping_jobs
                        SET contacts_extracted = (
                            SELECT COUNT(*) FROM scraped_contacts
                            WHERE job_id = :job_id
                        ),
                        updated_at = NOW()
                        WHERE id = :job_id
                    """),
                    {"job_id": job_id},
                )
        except Exception as e:
            logger.error(f"Failed to update contact count for job #{job_id}: {e}")


class ArticlePipeline:
    """Store scraped blog articles in PostgreSQL."""

    def __init__(self):
        self._count = 0

    def process_item(self, item, spider):
        if not isinstance(item, ArticleItem):
            return item

        with get_db_session() as session:
            session.execute(
                text("""
                INSERT INTO scraped_articles
                    (job_id, url, title, content_text, content_html, excerpt,
                     author, date_published, categories, tags,
                     external_links, internal_links, featured_image_url,
                     meta_description, word_count, language, domain,
                     country, region, city, extracted_category, extracted_subcategory,
                     year, month)
                VALUES
                    (:job_id, :url, :title, :content_text, :content_html, :excerpt,
                     :author, :date_published, :categories, :tags,
                     :external_links, :internal_links, :featured_image_url,
                     :meta_description, :word_count, :language, :domain,
                     :country, :region, :city, :extracted_category, :extracted_subcategory,
                     :year, :month)
                ON CONFLICT (url) DO UPDATE SET
                    title = EXCLUDED.title,
                    content_text = EXCLUDED.content_text,
                    content_html = EXCLUDED.content_html,
                    excerpt = EXCLUDED.excerpt,
                    author = EXCLUDED.author,
                    date_published = EXCLUDED.date_published,
                    categories = EXCLUDED.categories,
                    tags = EXCLUDED.tags,
                    external_links = EXCLUDED.external_links,
                    internal_links = EXCLUDED.internal_links,
                    featured_image_url = EXCLUDED.featured_image_url,
                    meta_description = EXCLUDED.meta_description,
                    word_count = EXCLUDED.word_count,
                    language = EXCLUDED.language,
                    country = EXCLUDED.country,
                    region = EXCLUDED.region,
                    city = EXCLUDED.city,
                    extracted_category = EXCLUDED.extracted_category,
                    extracted_subcategory = EXCLUDED.extracted_subcategory,
                    year = EXCLUDED.year,
                    month = EXCLUDED.month,
                    scraped_at = NOW()
                """),
                {
                    "job_id": item.get("job_id"),
                    "url": item["source_url"],
                    "title": item.get("title"),
                    "content_text": item.get("content_text"),
                    "content_html": item.get("content_html"),
                    "excerpt": item.get("excerpt"),
                    "author": item.get("author"),
                    "date_published": item.get("date_published"),
                    "categories": item.get("categories", []),
                    "tags": item.get("tags", []),
                    "external_links": json.dumps(item.get("external_links", [])),
                    "internal_links": json.dumps(item.get("internal_links", [])),
                    "featured_image_url": item.get("featured_image_url"),
                    "meta_description": item.get("meta_description"),
                    "word_count": item.get("word_count", 0),
                    "language": item.get("language"),
                    "domain": item.get("domain"),
                    "country": item.get("country"),
                    "region": item.get("region"),
                    "city": item.get("city"),
                    "extracted_category": item.get("extracted_category"),
                    "extracted_subcategory": item.get("extracted_subcategory"),
                    "year": item.get("year"),
                    "month": item.get("month"),
                },
            )

        self._count += 1
        if self._count % 5 == 0:
            self._update_job_progress(item.get("job_id"))

        logger.debug(f"Stored article: {item.get('title', 'untitled')}")
        return item

    def close_spider(self, spider):
        """Flush final progress on spider close."""
        job_id = getattr(spider, "job_id", None)
        if job_id:
            self._update_job_progress(job_id)

    def _update_job_progress(self, job_id):
        if not job_id:
            return
        try:
            with get_db_session() as session:
                session.execute(
                    text("""
                        UPDATE scraping_jobs
                        SET contacts_extracted = (
                            SELECT COUNT(*) FROM scraped_articles
                            WHERE job_id = :job_id
                        ),
                        updated_at = NOW()
                        WHERE id = :job_id
                    """),
                    {"job_id": int(job_id)},
                )
        except Exception as e:
            logger.error(f"Failed to update article count for job #{job_id}: {e}")
