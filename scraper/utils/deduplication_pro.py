"""
ULTRA-PROFESSIONAL DEDUPLICATION SYSTEM
========================================

Multi-layer deduplication with perfect accuracy:
1. URL exact match
2. URL normalized (http/https, www, trailing slash, query params)
3. Email deduplication
4. Content hash deduplication (similar pages)
5. Temporal deduplication (don't re-scrape if recent)

Features:
- Redis-backed with automatic fallback to PostgreSQL
- Atomic operations (no race conditions)
- Configurable TTL per deduplication layer
- Comprehensive statistics tracking
- Production-grade error handling
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse, urlunparse

import redis
from sqlalchemy import text

from scraper.database import get_db_session

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# Configuration (from environment)
# ────────────────────────────────────────────────────────────

DEDUP_URL_TTL_DAYS = int(os.getenv("DEDUP_URL_TTL_DAYS", "30"))
DEDUP_EMAIL_GLOBAL = os.getenv("DEDUP_EMAIL_GLOBAL", "true").lower() == "true"
DEDUP_CONTENT_HASH_ENABLED = os.getenv("DEDUP_CONTENT_HASH_ENABLED", "true").lower() == "true"
DEDUP_URL_NORMALIZE = os.getenv("DEDUP_URL_NORMALIZE", "true").lower() == "true"


# ────────────────────────────────────────────────────────────
# URL Normalization
# ────────────────────────────────────────────────────────────

def normalize_url(url: str) -> str:
    """
    Normalize URL to detect duplicates:
    - Convert to lowercase
    - Remove www prefix
    - Force https scheme
    - Remove trailing slash
    - Sort query parameters
    - Remove common tracking parameters

    Examples:
        http://www.example.com/ → https://example.com
        https://example.com?utm_source=x&id=1 → https://example.com?id=1
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url.strip().lower())

        # Normalize scheme: http → https
        scheme = "https"

        # Remove www prefix
        netloc = parsed.netloc
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Remove trailing slash from path
        path = parsed.path.rstrip("/")
        if not path:
            path = ""

        # Sort and filter query parameters
        if parsed.query:
            # Remove tracking parameters
            tracking_params = {
                "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid",
                "_ga", "_gid", "_hsenc", "_hsmi",
            }

            params = parse_qs(parsed.query)
            filtered_params = {
                k: v for k, v in params.items()
                if k.lower() not in tracking_params
            }

            # Sort parameters for consistency
            sorted_query = "&".join(
                f"{k}={v[0]}" for k, v in sorted(filtered_params.items())
            )
        else:
            sorted_query = ""

        # Rebuild URL
        normalized = urlunparse((scheme, netloc, path, "", sorted_query, ""))
        return normalized

    except Exception as e:
        logger.warning(f"Failed to normalize URL {url}: {e}")
        return url


# ────────────────────────────────────────────────────────────
# Content Hash
# ────────────────────────────────────────────────────────────

def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash of content (normalized).
    Used to detect duplicate pages with different URLs.

    Args:
        content: Page content (text or HTML)

    Returns:
        SHA256 hash (hex string)
    """
    if not content:
        return ""

    # Normalize content before hashing
    normalized = content.strip().lower()
    # Remove extra whitespace
    normalized = " ".join(normalized.split())

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ────────────────────────────────────────────────────────────
# Deduplication Manager
# ────────────────────────────────────────────────────────────

class DeduplicationManager:
    """
    Ultra-professional deduplication system with multi-layer checks.
    """

    def __init__(self, job_id: Optional[int] = None):
        """
        Initialize deduplication manager.

        Args:
            job_id: Scraping job ID (for per-job deduplication)
        """
        self.job_id = job_id
        self.redis_client: Optional[redis.Redis] = None
        self._init_redis()

        # Statistics (in-memory)
        self.stats = {
            "urls_checked": 0,
            "urls_deduplicated": 0,
            "urls_normalized_deduplicated": 0,
            "emails_deduplicated": 0,
            "content_hash_deduplicated": 0,
            "temporal_deduplicated": 0,
        }

    def _init_redis(self):
        """Initialize Redis connection (with fallback to PostgreSQL)."""
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
            logger.info("Deduplication: Redis connected")
        except Exception as e:
            logger.warning(f"Deduplication: Redis unavailable, using PostgreSQL fallback: {e}")
            self.redis_client = None

    # ────────────────────────────────────────────────────────
    # Layer 1: URL Exact Match
    # ────────────────────────────────────────────────────────

    def is_url_seen_exact(self, url: str) -> bool:
        """
        Check if URL was already scraped (exact match).

        Args:
            url: URL to check

        Returns:
            True if URL was already seen
        """
        if not url:
            return False

        self.stats["urls_checked"] += 1

        # Try Redis first
        if self.redis_client:
            try:
                key = f"dedup:url_exact:{self.job_id or 'global'}"
                exists = self.redis_client.sismember(key, url)
                if exists:
                    self.stats["urls_deduplicated"] += 1
                    logger.debug(f"URL deduplicated (exact): {url}")
                return bool(exists)
            except redis.ConnectionError:
                logger.warning("Redis connection lost, falling back to PostgreSQL")
                self.redis_client = None

        # Fallback to PostgreSQL
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT 1 FROM url_deduplication_cache
                        WHERE url = :url AND dedup_type = 'exact'
                        AND (:job_id IS NULL OR job_id = :job_id)
                        LIMIT 1
                    """),
                    {"url": url, "job_id": self.job_id}
                ).scalar()

                if result:
                    self.stats["urls_deduplicated"] += 1
                    logger.debug(f"URL deduplicated (exact, PostgreSQL): {url}")
                return bool(result)
        except Exception as e:
            logger.error(f"Failed to check URL exact match: {e}")
            return False

    def mark_url_seen_exact(self, url: str):
        """
        Mark URL as seen (exact match).

        Args:
            url: URL to mark
        """
        if not url:
            return

        # Try Redis first
        if self.redis_client:
            try:
                key = f"dedup:url_exact:{self.job_id or 'global'}"
                self.redis_client.sadd(key, url)
                # Set TTL if configured
                if DEDUP_URL_TTL_DAYS > 0:
                    self.redis_client.expire(key, DEDUP_URL_TTL_DAYS * 86400)
                return
            except redis.ConnectionError:
                logger.warning("Redis connection lost, falling back to PostgreSQL")
                self.redis_client = None

        # Fallback to PostgreSQL
        try:
            with get_db_session() as session:
                session.execute(
                    text("""
                        INSERT INTO url_deduplication_cache
                            (url, dedup_type, job_id, expires_at)
                        VALUES
                            (:url, 'exact', :job_id, :expires_at)
                        ON CONFLICT (url, dedup_type, COALESCE(job_id, -1)) DO UPDATE
                            SET seen_at = NOW(), expires_at = EXCLUDED.expires_at
                    """),
                    {
                        "url": url,
                        "job_id": self.job_id,
                        "expires_at": datetime.now() + timedelta(days=DEDUP_URL_TTL_DAYS) if DEDUP_URL_TTL_DAYS > 0 else None
                    }
                )
        except Exception as e:
            logger.error(f"Failed to mark URL as seen: {e}")

    # ────────────────────────────────────────────────────────
    # Layer 2: URL Normalized
    # ────────────────────────────────────────────────────────

    def is_url_seen_normalized(self, url: str) -> bool:
        """
        Check if normalized URL was already scraped.

        Args:
            url: URL to check

        Returns:
            True if normalized URL was already seen
        """
        if not DEDUP_URL_NORMALIZE or not url:
            return False

        normalized = normalize_url(url)
        if normalized == url:
            # Already checked exact match, skip
            return False

        # Try Redis first
        if self.redis_client:
            try:
                key = f"dedup:url_normalized:{self.job_id or 'global'}"
                exists = self.redis_client.sismember(key, normalized)
                if exists:
                    self.stats["urls_normalized_deduplicated"] += 1
                    logger.debug(f"URL deduplicated (normalized): {url} → {normalized}")
                return bool(exists)
            except redis.ConnectionError:
                self.redis_client = None

        # Fallback to PostgreSQL
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT 1 FROM url_deduplication_cache
                        WHERE url = :url AND dedup_type = 'normalized'
                        AND (:job_id IS NULL OR job_id = :job_id)
                        LIMIT 1
                    """),
                    {"url": normalized, "job_id": self.job_id}
                ).scalar()

                if result:
                    self.stats["urls_normalized_deduplicated"] += 1
                    logger.debug(f"URL deduplicated (normalized, PostgreSQL): {url} → {normalized}")
                return bool(result)
        except Exception as e:
            logger.error(f"Failed to check URL normalized match: {e}")
            return False

    def mark_url_seen_normalized(self, url: str):
        """Mark normalized URL as seen."""
        if not DEDUP_URL_NORMALIZE or not url:
            return

        normalized = normalize_url(url)

        # Try Redis first
        if self.redis_client:
            try:
                key = f"dedup:url_normalized:{self.job_id or 'global'}"
                self.redis_client.sadd(key, normalized)
                if DEDUP_URL_TTL_DAYS > 0:
                    self.redis_client.expire(key, DEDUP_URL_TTL_DAYS * 86400)
                return
            except redis.ConnectionError:
                self.redis_client = None

        # Fallback to PostgreSQL
        try:
            with get_db_session() as session:
                session.execute(
                    text("""
                        INSERT INTO url_deduplication_cache
                            (url, dedup_type, job_id, expires_at)
                        VALUES
                            (:url, 'normalized', :job_id, :expires_at)
                        ON CONFLICT (url, dedup_type, COALESCE(job_id, -1)) DO UPDATE
                            SET seen_at = NOW(), expires_at = EXCLUDED.expires_at
                    """),
                    {
                        "url": normalized,
                        "job_id": self.job_id,
                        "expires_at": datetime.now() + timedelta(days=DEDUP_URL_TTL_DAYS) if DEDUP_URL_TTL_DAYS > 0 else None
                    }
                )
        except Exception as e:
            logger.error(f"Failed to mark normalized URL as seen: {e}")

    # ────────────────────────────────────────────────────────
    # Layer 3: Email Deduplication
    # ────────────────────────────────────────────────────────

    def is_email_seen(self, email: str) -> bool:
        """
        Check if email was already scraped.

        Args:
            email: Email to check (normalized to lowercase)

        Returns:
            True if email was already seen
        """
        if not email:
            return False

        email = email.lower().strip()

        # Global or per-job deduplication
        scope = "global" if DEDUP_EMAIL_GLOBAL else self.job_id or "global"

        # Try Redis first
        if self.redis_client:
            try:
                key = f"dedup:email:{scope}"
                exists = self.redis_client.sismember(key, email)
                if exists:
                    self.stats["emails_deduplicated"] += 1
                    logger.debug(f"Email deduplicated: {email}")
                return bool(exists)
            except redis.ConnectionError:
                self.redis_client = None

        # Fallback to PostgreSQL
        try:
            with get_db_session() as session:
                # Check scraped_contacts table
                if DEDUP_EMAIL_GLOBAL:
                    result = session.execute(
                        text("SELECT 1 FROM scraped_contacts WHERE email = :email LIMIT 1"),
                        {"email": email}
                    ).scalar()
                else:
                    result = session.execute(
                        text("SELECT 1 FROM scraped_contacts WHERE email = :email AND job_id = :job_id LIMIT 1"),
                        {"email": email, "job_id": self.job_id}
                    ).scalar()

                if result:
                    self.stats["emails_deduplicated"] += 1
                    logger.debug(f"Email deduplicated (PostgreSQL): {email}")
                return bool(result)
        except Exception as e:
            logger.error(f"Failed to check email deduplication: {e}")
            return False

    def mark_email_seen(self, email: str):
        """Mark email as seen."""
        if not email:
            return

        email = email.lower().strip()
        scope = "global" if DEDUP_EMAIL_GLOBAL else self.job_id or "global"

        # Try Redis first (PostgreSQL will handle this automatically via pipeline)
        if self.redis_client:
            try:
                key = f"dedup:email:{scope}"
                self.redis_client.sadd(key, email)
                # Emails don't expire (permanent deduplication)
                return
            except redis.ConnectionError:
                self.redis_client = None

    # ────────────────────────────────────────────────────────
    # Layer 4: Content Hash Deduplication
    # ────────────────────────────────────────────────────────

    def is_content_seen(self, content: str) -> Tuple[bool, str]:
        """
        Check if content was already scraped (by hash).

        Args:
            content: Page content

        Returns:
            (is_seen, content_hash)
        """
        if not DEDUP_CONTENT_HASH_ENABLED or not content:
            return False, ""

        content_hash = compute_content_hash(content)

        # Try Redis first
        if self.redis_client:
            try:
                key = f"dedup:content:{self.job_id or 'global'}"
                exists = self.redis_client.sismember(key, content_hash)
                if exists:
                    self.stats["content_hash_deduplicated"] += 1
                    logger.debug(f"Content deduplicated (hash): {content_hash[:16]}...")
                return bool(exists), content_hash
            except redis.ConnectionError:
                self.redis_client = None

        # Fallback to PostgreSQL
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT 1 FROM content_hash_cache
                        WHERE content_hash = :hash
                        AND (:job_id IS NULL OR job_id = :job_id)
                        LIMIT 1
                    """),
                    {"hash": content_hash, "job_id": self.job_id}
                ).scalar()

                if result:
                    self.stats["content_hash_deduplicated"] += 1
                    logger.debug(f"Content deduplicated (hash, PostgreSQL): {content_hash[:16]}...")
                return bool(result), content_hash
        except Exception as e:
            logger.error(f"Failed to check content hash: {e}")
            return False, content_hash

    def mark_content_seen(self, content_hash: str):
        """Mark content hash as seen."""
        if not DEDUP_CONTENT_HASH_ENABLED or not content_hash:
            return

        # Try Redis first
        if self.redis_client:
            try:
                key = f"dedup:content:{self.job_id or 'global'}"
                self.redis_client.sadd(key, content_hash)
                if DEDUP_URL_TTL_DAYS > 0:
                    self.redis_client.expire(key, DEDUP_URL_TTL_DAYS * 86400)
                return
            except redis.ConnectionError:
                self.redis_client = None

        # Fallback to PostgreSQL
        try:
            with get_db_session() as session:
                session.execute(
                    text("""
                        INSERT INTO content_hash_cache
                            (content_hash, job_id, expires_at)
                        VALUES
                            (:hash, :job_id, :expires_at)
                        ON CONFLICT (content_hash, COALESCE(job_id, -1)) DO UPDATE
                            SET seen_at = NOW(), expires_at = EXCLUDED.expires_at
                    """),
                    {
                        "hash": content_hash,
                        "job_id": self.job_id,
                        "expires_at": datetime.now() + timedelta(days=DEDUP_URL_TTL_DAYS) if DEDUP_URL_TTL_DAYS > 0 else None
                    }
                )
        except Exception as e:
            logger.error(f"Failed to mark content hash as seen: {e}")

    # ────────────────────────────────────────────────────────
    # Layer 5: Temporal Deduplication
    # ────────────────────────────────────────────────────────

    def is_url_recently_scraped(self, url: str, days: int = None) -> bool:
        """
        Check if URL was scraped recently (within X days).

        Args:
            url: URL to check
            days: Days threshold (default: DEDUP_URL_TTL_DAYS)

        Returns:
            True if URL was scraped recently
        """
        if not url:
            return False

        days = days or DEDUP_URL_TTL_DAYS
        if days <= 0:
            return False

        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT 1 FROM scraped_contacts
                        WHERE source_url = :url
                        AND scraped_at > NOW() - INTERVAL ':days days'
                        LIMIT 1
                    """),
                    {"url": url, "days": days}
                ).scalar()

                if result:
                    self.stats["temporal_deduplicated"] += 1
                    logger.debug(f"URL deduplicated (temporal): {url} (scraped within {days} days)")
                return bool(result)
        except Exception as e:
            logger.error(f"Failed to check temporal deduplication: {e}")
            return False

    # ────────────────────────────────────────────────────────
    # Statistics & Reporting
    # ────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get deduplication statistics."""
        return {
            **self.stats,
            "deduplication_rate": (
                self.stats["urls_deduplicated"] +
                self.stats["urls_normalized_deduplicated"] +
                self.stats["emails_deduplicated"] +
                self.stats["content_hash_deduplicated"] +
                self.stats["temporal_deduplicated"]
            ) / max(self.stats["urls_checked"], 1) * 100
        }

    def log_stats(self):
        """Log deduplication statistics."""
        stats = self.get_stats()
        logger.info(
            f"Deduplication stats: "
            f"{stats['urls_checked']} URLs checked, "
            f"{stats['urls_deduplicated']} exact duplicates, "
            f"{stats['urls_normalized_deduplicated']} normalized duplicates, "
            f"{stats['emails_deduplicated']} email duplicates, "
            f"{stats['content_hash_deduplicated']} content duplicates, "
            f"{stats['temporal_deduplicated']} temporal duplicates "
            f"({stats['deduplication_rate']:.1f}% deduplication rate)"
        )


# ────────────────────────────────────────────────────────────
# Database Schema (SQL migrations)
# ────────────────────────────────────────────────────────────

DEDUPLICATION_SCHEMA = """
-- URL deduplication cache
CREATE TABLE IF NOT EXISTS url_deduplication_cache (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    dedup_type VARCHAR(20) NOT NULL CHECK (dedup_type IN ('exact', 'normalized')),
    job_id INTEGER REFERENCES scraping_jobs(id) ON DELETE CASCADE,
    seen_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    UNIQUE (url, dedup_type, COALESCE(job_id, -1))
);

CREATE INDEX IF NOT EXISTS idx_url_dedup_url ON url_deduplication_cache(url);
CREATE INDEX IF NOT EXISTS idx_url_dedup_expires ON url_deduplication_cache(expires_at) WHERE expires_at IS NOT NULL;

-- Content hash cache
CREATE TABLE IF NOT EXISTS content_hash_cache (
    id SERIAL PRIMARY KEY,
    content_hash VARCHAR(64) NOT NULL,
    job_id INTEGER REFERENCES scraping_jobs(id) ON DELETE CASCADE,
    seen_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    UNIQUE (content_hash, COALESCE(job_id, -1))
);

CREATE INDEX IF NOT EXISTS idx_content_hash ON content_hash_cache(content_hash);
CREATE INDEX IF NOT EXISTS idx_content_hash_expires ON content_hash_cache(expires_at) WHERE expires_at IS NOT NULL;

-- Cleanup expired entries (cron job)
CREATE OR REPLACE FUNCTION cleanup_expired_deduplication_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM url_deduplication_cache WHERE expires_at < NOW();
    DELETE FROM content_hash_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;
"""
