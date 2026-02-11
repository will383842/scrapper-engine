"""Spider runner - launches Scrapy spiders from the API."""

import json
import logging
import os
import subprocess
import sys
import threading

from scraper.database import get_db_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Spider class registry
SPIDER_MAP = {
    "google_search": "google_search",
    "google_maps": "google_maps",
    "custom_urls": "generic_urls",
    "blog_content": "blog_content",
}


def run_spider(job_id: int, source_type: str, config: dict, resume: bool = False):
    """
    Launch a Scrapy spider in a subprocess (avoids ReactorNotRestartable).
    Updates job status in the database.
    If resume=True, passes the resume flag to the spider for checkpoint recovery.
    """
    spider_name = SPIDER_MAP.get(source_type)
    if not spider_name:
        logger.error(f"Unknown source_type: {source_type}")
        _update_job_status(job_id, "failed")
        return

    def _run():
        try:
            _update_job_status(job_id, "running")

            # Build scrapy crawl command
            cmd = [
                sys.executable, "-m", "scrapy", "crawl", spider_name,
                "-a", f"job_id={job_id}",
            ]

            # Pass resume flag if resuming
            if resume:
                cmd.extend(["-a", "resume=true"])

            # Pass spider config as arguments
            for key, value in config.items():
                if isinstance(value, list):
                    cmd.extend(["-a", f"{key}={json.dumps(value)}"])
                else:
                    cmd.extend(["-a", f"{key}={value}"])

            logger.info(f"Launching spider: {' '.join(cmd)}")

            # Use project root as cwd (works in Docker and local)
            cwd = os.getenv("SCRAPER_CWD", "/app")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour max
                cwd=cwd,
            )

            if result.returncode == 0:
                _update_job_status(job_id, "completed")
                logger.info(f"Spider completed for job #{job_id}")
            else:
                logger.error(
                    f"Spider failed for job #{job_id}: "
                    f"exit={result.returncode} stderr={result.stderr[:500]}"
                )
                _update_job_status(job_id, "failed")

        except subprocess.TimeoutExpired:
            logger.error(f"Spider timed out for job #{job_id}")
            _update_job_status(job_id, "failed")
        except Exception as e:
            logger.error(f"Spider failed for job #{job_id}: {e}")
            _update_job_status(job_id, "failed")

    thread = threading.Thread(target=_run, daemon=True, name=f"spider-job-{job_id}")
    thread.start()
    logger.info(f"Spider launched in background for job #{job_id}")


def _update_job_status(job_id: int, status: str):
    """Update a job's status in the database."""
    try:
        with get_db_session() as session:
            if status == "running":
                session.execute(
                    text("UPDATE scraping_jobs SET status = :status, started_at = NOW() WHERE id = :id"),
                    {"status": status, "id": job_id},
                )
            elif status in ("completed", "failed"):
                session.execute(
                    text("UPDATE scraping_jobs SET status = :status, completed_at = NOW() WHERE id = :id"),
                    {"status": status, "id": job_id},
                )
            else:
                session.execute(
                    text("UPDATE scraping_jobs SET status = :status WHERE id = :id"),
                    {"status": status, "id": job_id},
                )
    except Exception as e:
        logger.error(f"Failed to update job #{job_id} status to {status}: {e}")
