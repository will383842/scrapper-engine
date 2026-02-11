"""Checkpoint and URL fingerprint services for spider resume support."""

import hashlib
import json
import logging
from urllib.parse import urlparse

from scraper.database import get_db_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


# --- Checkpoint save/load ---

def save_checkpoint(job_id: int, data: dict) -> None:
    """Save checkpoint data to the scraping_jobs table."""
    try:
        with get_db_session() as session:
            session.execute(
                text("""
                    UPDATE scraping_jobs
                    SET checkpoint_data = :data, updated_at = NOW()
                    WHERE id = :job_id
                """),
                {"data": json.dumps(data), "job_id": job_id},
            )
        logger.debug(f"Checkpoint saved for job #{job_id}: {data}")
    except Exception as e:
        logger.error(f"Failed to save checkpoint for job #{job_id}: {e}")


def load_checkpoint(job_id: int) -> dict:
    """Load checkpoint data from the scraping_jobs table."""
    try:
        with get_db_session() as session:
            result = session.execute(
                text("SELECT checkpoint_data FROM scraping_jobs WHERE id = :job_id"),
                {"job_id": job_id},
            ).scalar()
            if result:
                return result if isinstance(result, dict) else json.loads(result)
    except Exception as e:
        logger.error(f"Failed to load checkpoint for job #{job_id}: {e}")
    return {}


def update_progress(job_id: int, progress: float, pages: int = 0, contacts: int = 0) -> None:
    """Update job progress in the database."""
    try:
        with get_db_session() as session:
            session.execute(
                text("""
                    UPDATE scraping_jobs
                    SET progress = :progress,
                        pages_scraped = GREATEST(pages_scraped, :pages),
                        contacts_extracted = :contacts,
                        updated_at = NOW()
                    WHERE id = :job_id
                """),
                {
                    "progress": min(progress, 100.0),
                    "pages": pages,
                    "contacts": contacts,
                    "job_id": job_id,
                },
            )
    except Exception as e:
        logger.error(f"Failed to update progress for job #{job_id}: {e}")


# --- URL Fingerprinting ---

def _hash_url(url: str) -> str:
    """Normalize and hash a URL for deduplication."""
    parsed = urlparse(url)
    # Normalize: lowercase scheme+host, remove trailing slash, keep path+query
    normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return hashlib.sha256(normalized.encode()).hexdigest()


def is_url_seen(url: str) -> bool:
    """Check if a URL has already been scraped (using url_fingerprints table)."""
    url_hash = _hash_url(url)
    try:
        with get_db_session() as session:
            result = session.execute(
                text("SELECT id FROM url_fingerprints WHERE url_hash = :hash"),
                {"hash": url_hash},
            ).scalar()
            return result is not None
    except Exception as e:
        logger.error(f"URL fingerprint check failed: {e}")
        return False


def mark_url_seen(url: str, spider_name: str = "") -> None:
    """Record a URL as visited in the url_fingerprints table."""
    url_hash = _hash_url(url)
    parsed = urlparse(url)
    normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
    if parsed.query:
        normalized += f"?{parsed.query}"

    try:
        with get_db_session() as session:
            session.execute(
                text("""
                    INSERT INTO url_fingerprints (url_normalized, url_hash, domain, spider_name)
                    VALUES (:url, :hash, :domain, :spider)
                    ON CONFLICT (url_hash) DO UPDATE SET
                        last_seen = NOW(),
                        visit_count = url_fingerprints.visit_count + 1
                """),
                {
                    "url": normalized,
                    "hash": url_hash,
                    "domain": parsed.netloc.lower(),
                    "spider": spider_name,
                },
            )
    except Exception as e:
        logger.error(f"Failed to mark URL as seen: {e}")


def get_completed_urls_for_job(job_id: int) -> set:
    """Get the set of already-completed source URLs for a job (from scraped_contacts)."""
    try:
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT DISTINCT source_url FROM scraped_contacts
                    WHERE job_id = :job_id AND source_url IS NOT NULL
                """),
                {"job_id": job_id},
            ).scalars().all()
            return set(results)
    except Exception as e:
        logger.error(f"Failed to get completed URLs for job #{job_id}: {e}")
        return set()
