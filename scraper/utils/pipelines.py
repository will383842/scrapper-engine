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
from sqlalchemy import text

logger = logging.getLogger(__name__)


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
                if self.redis_client.sismember(cache_key, email):
                    raise DropItem(f"Duplicate email: {email}")
                self.redis_client.sadd(cache_key, email)
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
                     meta_description, word_count, language, domain)
                VALUES
                    (:job_id, :url, :title, :content_text, :content_html, :excerpt,
                     :author, :date_published, :categories, :tags,
                     :external_links, :internal_links, :featured_image_url,
                     :meta_description, :word_count, :language, :domain)
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
